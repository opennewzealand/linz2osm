from xml.etree import ElementTree
import hashlib
from cStringIO import StringIO

from django.db import connection, connections
from django.conf import settings
from django.contrib.gis import geos
from django.utils import simplejson
from django.core.cache import cache

class Error(Exception):
    pass

def get_srtext_from_srid(srid):
    cursor = connection.cursor()
    cursor.execute('SELECT srtext FROM spatial_ref_sys WHERE srid=%s;', [srid])
    return cursor.fetchone()[0]

def get_layer_geometry_type(database_id, layer):
    """ Returns a (geometry_type, srid) tuple """
    cursor = connections[database_id].cursor()
    cursor.execute('SELECT type,srid FROM geometry_columns WHERE f_table_name=%s;', [layer.name])
    r = cursor.fetchone()
    return tuple(r[:2])

def get_layer_feature_ids(layer_in_dataset, extent=None, feature_limit=None):
    cursor = connections[layer_in_dataset.dataset.name].cursor()

    sql = 'SELECT ogc_fid FROM %s'
    params = []
    
    if extent:
        srid = layer_in_dataset.dataset.srid
        extent_trans = extent.hexewkb
        sql += ' WHERE (wkb_geometry && ST_Transform(%%s, %%s)) AND ST_CoveredBy(ST_Centroid(wkb_geometry), ST_Transform(%%s, %%s))'
        params += [extent_trans, srid, extent_trans, srid]

    sql += ' ORDER BY ogc_fid'
    if feature_limit:
        sql += ' LIMIT %d' % (feature_limit + 1)

    cursor.execute(sql % layer_in_dataset.layer.name, params)
    if (feature_limit is not None) and cursor.rowcount > feature_limit:
        return None # FIXME: use exceptions - should have checked feature count before approving workslice
    return [r[0] for r in cursor.fetchall()]
        

def get_layer_feature_count(database_id, layer, intersect_geom=None):
    cursor = connections[database_id].cursor()
    layer_srid = get_layer_geometry_type(database_id, layer)[1]
    if intersect_geom and intersect_geom.srid is None:
        intersect_geom.srid = layer_srid
    
    sql = 'SELECT count(*) FROM %s'
    params = []
    if intersect_geom:
        intersect_trans = intersect_geom.hexewkb
        sql += ' WHERE wkb_geometry && ST_Transform(%%s, %%s) AND ST_CoveredBy(ST_Centroid(wkb_geometry), ST_Transform(%%s, %%s))'
        params += [intersect_trans, layer_srid, intersect_trans, layer_srid]

    cursor.execute(sql % layer.name, params) 
    return cursor.fetchone()[0]
    
def get_layer_stats(database_id, layer):
    geom_type, srid = get_layer_geometry_type(database_id, layer)
    cursor = connections[database_id].cursor()

    # Expand bounds by 1,001 metres
    cursor.execute("SELECT ST_AsHexEWKB(ST_Transform(ST_SetSRID(ST_Envelope(ST_Buffer(ST_Extent(wkb_geometry), 1001.0)), %d), 4326)) FROM %s;" % (srid, layer.name))
    extent = geos.GEOSGeometry(cursor.fetchone()[0])
    
    r = {
        'feature_count': get_layer_feature_count(database_id, layer),
        'extent': extent,
        'fields': {}
    }
    
    cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s AND column_name NOT IN ('ogc_fid', 'wkb_geometry');", [layer.name])
    for col_name,col_type in cursor.fetchall():
        sql = 'SELECT count(*) FROM %(t)s WHERE %(c)s IS NOT NULL'
        if col_type in ('character varying',):
            sql += " AND %(c)s <> ''"
        elif col_type in ('double precision', 'integer',):
            sql += " AND %(c)s <> 0"
        cursor.execute(sql % {'t': layer.name, 'c': col_name}) 
        r['fields'][col_name] = {
            'non_empty_pc' : cursor.fetchone()[0] / float(r['feature_count']) * 100.0,
        }
    
    if geom_type in ('LINESTRING', 'POLYGON'):
        cursor.execute("SELECT avg(ST_NPoints(wkb_geometry)), max(ST_NPoints(wkb_geometry)) FROM %s;" % layer.name)
        s = cursor.fetchone();
        r.update({
            'points_avg': s[0],
            'points_max': s[1],
        })        
    
    if geom_type == 'POLYGON':
        cursor.execute("SELECT avg(ST_NRings(wkb_geometry)), max(ST_NRings(wkb_geometry)), avg(ST_NPoints(ST_ExteriorRing(wkb_geometry))), max(ST_NPoints(ST_ExteriorRing(wkb_geometry))) FROM %s;" % layer.name)
        s = cursor.fetchone();
        r.update({
            'rings_avg': s[0],
            'rings_max': s[1],
            'points_ext_ring_avg': s[2],
            'points_ext_ring_max': s[3],
        })
    
    return r
    

def clean_data(cell):
    if isinstance(cell, unicode) or isinstance(cell, str):
        return cell.strip()
    else:
        return cell

def export(workslice):
    dataset = workslice.layer_in_dataset.dataset
    database_id = dataset.name
    layer = workslice.layer_in_dataset.layer
    cursor = connections[database_id].cursor()
    db_info = settings.DATABASES[database_id]
    
    cursor.execute('SELECT column_name,udt_name FROM information_schema.columns WHERE table_name=%s;', [layer.name])
    data_columns = []
    geom_column = None
    for column_name,udt_name in cursor:
        if udt_name == 'geometry':
            geom_column = column_name
        else:
            data_columns.append(column_name)
    
    layer_tags = layer.get_all_tags()
    processors = layer.get_processors()
    
    writer = OSMWriter(id_hash=(database_id, layer.name))
    
    columns = ['st_asbinary(st_transform(st_setsrid("%s", %d), 4326)) AS geom' % (geom_column, dataset.srid)] + ['"%s"' % c for c in data_columns]
    sql_base = 'SELECT %s FROM "%s"' % (",".join(columns), layer.name)

    sql_base += ' WHERE ogc_fid IN (%s)' % workslice.formatted_feature_id_list()

    cursor.execute(sql_base)
    
    for i,row in enumerate(cursor):
        if row[0] is None:
            continue
        row_geom = geos.GEOSGeometry(row[0])
        if row_geom.empty:
            continue
        
        row_data = dict(zip(data_columns,[clean_data(c) for c in row[1:] ]))
        row_data['layer_name'] = layer.name
        row_data['dataset_name'] = dataset.name
        row_data['workslice_id'] = workslice.id
        
        row_tags = {}
        for tag in layer_tags:
            try:
                v = tag.eval(row_data)
            except tag.ScriptError, e:
                emsg = "Error evaluating '%s' tag against record:\n" % tag
                emsg += simplejson.dumps(e.data, indent=2) + "\n"
                emsg += str(e)
                raise Error(emsg)
            if (v is not None) and (v != ""):
                row_tags[tag.tag] = v

        # apply geometry processing
        for p in processors:
            row_geom = p.process(row_geom, fields=row_data, tags=row_tags, id=i)

        writer.add_feature(row_geom, row_tags)

    return writer.xml()

class OSMWriter(object):
    WAY_SPLIT_SIZE = 495
    
    def __init__(self, id_hash=None, processors=None):
        self.n_root = ElementTree.Element('osmChange', version="0.6", generator="linz2osm")
        self.n_create = ElementTree.SubElement(self.n_root, 'create', version="0.6", generator="linz2osm")
        self.tree = ElementTree.ElementTree(self.n_root)
        self._nodes = {}

        if id_hash is None:
            self._id = 0
        else:
            h = hashlib.sha1(unicode(id_hash).encode('utf8')).hexdigest()
            self._id = -1 * int(h[:6], 16)
    
        self.processors = processors or []
    
    def add_feature(self, geom, tags=None):
        self.build_geom(geom, tags)
    
    def xml(self):
        # prettify - ok to call more than once
        self._etree_indent(self.tree.getroot())
    
        s = StringIO()
        self.tree.write(s, 'utf-8')
        s.write('\n')
        return s.getvalue()
    
    @property
    def next_id(self):
        """ Return a unique ID. """
        self._id -= 1
        return str(self._id)
    
    def build_polygon(self, geom, tags, root=None):
        if root is None: 
            r = ElementTree.Element('relation', id=self.next_id)
            ElementTree.SubElement(r, 'tag', k='type', v='multipolygon')
            self.build_tags(r, tags)
        else:
            r = root
        
        if isinstance(geom, geos.MultiPolygon):
            for g in geom:
                self.build_polygon(g, tags, r)
        else:
            for i,ring in enumerate(geom):
                is_outer = (i == 0)
                w_tags = tags if is_outer else None
                w_ids = self.build_way(ring.tuple, w_tags)
                for w_id in w_ids:
                    ElementTree.SubElement(r, 'member', type="way", ref=w_id, role=('outer' if (i == 0) else 'inner'))

        if root is None:
            self.n_create.append(r)
        return [r.get('id')]
            
    def build_way(self, coords, tags):
        ids = []
        rem_coords = coords[:]
        node_map = {}
        while True:
            w = ElementTree.Element('way', id=self.next_id)
            
            cur_coords = rem_coords[:self.WAY_SPLIT_SIZE]
            rem_coords = rem_coords[self.WAY_SPLIT_SIZE-1:]
                        
            for i,c in enumerate(cur_coords):
                n_id = self._node(c, None)
                ElementTree.SubElement(w, 'nd', ref=n_id)
            self.build_tags(w, tags)
            self.n_create.append(w)
            ids.append(w.get('id'))
            
            if len(rem_coords) < 2:
                break
        
        return ids

    def _node(self, coords, tags, map=True):
        k = (str(coords[0]), str(coords[1]), id(tags) if tags else None)
        n = self._nodes.get(k)
        if (not map) or (n is None):
            n = ElementTree.SubElement(self.n_create, 'node', id=self.next_id, lat=str(coords[1]), lon=str(coords[0]))
            self.build_tags(n, tags)
            if map:
                self._nodes[k] = n
        return n.get('id')

    def build_node(self, geom, tags, map=True):
        return [self._node((geom.x, geom.y), tags, map)]
    
    def build_geom(self, geom, tags, inner=False):
        if isinstance(geom, geos.Polygon) and (len(geom) == 1) and (len(geom[0]) <= self.WAY_SPLIT_SIZE):
            # short single-ring polygons are built as ways
            return self.build_way(geom[0].tuple, tags)
            
        elif isinstance(geom, (geos.MultiPolygon, geos.Polygon)):
            return self.build_polygon(geom, tags)
    
        elif isinstance(geom, geos.GeometryCollection):
            # FIXME: Link together as a relation?
            ids = []
            for g in geom:
                ids += self.build_geom(g, tags, inner=True)
            return ids
        
        elif isinstance(geom, geos.Point):
            # node
            # indepenent nodes are mapped (ie. POINTs)
            # repeated nodes within a MULTIPOINT/GEOMETRYCOLLECTION are mapped
            return self.build_node(geom, tags, map=inner)
        
        elif isinstance(geom, geos.LineString):
            # way
            return self.build_way(geom.tuple, tags)
    
    def build_tags(self, parent_node, tags):
        if tags:
            for tn,tv in tags.items():
                if len(tn) > 255:
                    raise Error(u'Tag key too long (max. 255 chars): %s' % tn)
                tv = unicode(tv)
                if len(tv) > 255:
                    raise Error(u'Tag value too long (max. 255 chars): %s' % tv)
                ElementTree.SubElement(parent_node, 'tag', k=tn, v=tv)
    
    def _etree_indent(self, elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            for e in elem:
                self._etree_indent(e, level+1)
            if not e.tail or not e.tail.strip():
                e.tail = i
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
