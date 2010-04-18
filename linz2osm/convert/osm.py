from xml.etree import ElementTree
import hashlib
from cStringIO import StringIO

from django.db import connections
from django.conf import settings
from django.contrib.gis import geos
from django.utils import simplejson
from django.core.cache import cache

class Error(Exception):
    pass

def get_layer_datasets(layer):
    r = cache.get('convert:osm:layer_datasets:%s' % layer.name)
    if r is None:
        r = []
        for ds_id, ds_info in settings.DATABASES.items():
            if ds_id == 'default':
                continue
            if has_layer(ds_id, layer):
                r.append((ds_id, ds_info.get('_description', ds_id),))
        cache.set('convert:osm:layer_datasets:%s' % layer, r, 60*60*24)
    return r

def has_layer(database_id, layer):
    r = cache.get('convert:osm:has_layer:%s:%s' % (database_id, layer.name))
    if r is None:
        cursor = connections[database_id].cursor()
        cursor.execute('SELECT count(*) FROM information_schema.tables WHERE table_name=%s;', [layer.name])
        count = cursor.fetchone()[0]
        r = (count == 1)
        cache.set('convert:osm:has_layer:%s:%s' % (database_id, layer.name), r, 60*60*24)
    return r

def dataset_tables(database_id):
    r = cache.get('convert:osm:dataset_tables:%s' % database_id)
    if r is None:
        cursor = connections[database_id].cursor()
        cursor.execute('SELECT table_name FROM information_schema.tables;')
        r = [row[0] for row in cursor]
        cache.set('convert:osm:dataset_tables:%s' % database_id, r, 60*60*24)
    return r

def export(database_id, layer, bbox=None):
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
    
    writer = OSMWriter(id_hash=(database_id, layer.name))
    
    columns = ['st_asbinary(st_transform(st_setsrid("%s", %d), 4326)) AS geom' % (geom_column, db_info['_srid'])] + ['"%s"' % c for c in data_columns]
    sql_base = 'SELECT %s FROM "%s"' % (",".join(columns), layer.name)
    if bbox is None:
        cursor.execute(sql_base)
    else:
        sql = sql_base + ' WHERE setsrid(%s,%d) && st_transform(st_setsrid(ST_MakeBox2D(ST_MakePoint(%%s, %%s), ST_MakePoint(%%s, %%s)), 4326), %d)' % (geom_column, db_info['_srid'], db_info['_srid'])
        cursor.execute(sql, bbox)
    
    for row in cursor:
        if row[0] is None:
            continue
        row_geom = geos.GEOSGeometry(row[0])
        if row_geom.empty:
            continue
        
        row_data = dict(zip(data_columns,row[1:]))
        
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

        writer.add_feature(row_geom, row_tags)

    return writer.xml()

class OSMWriter(object):
    WAY_SPLIT_SIZE = 495
    
    def __init__(self, id_hash=None):
        self.n_root = ElementTree.Element('osmChange', version="0.6", generator="linz2osm")
        self.n_create = ElementTree.SubElement(self.n_root, 'create', version="0.6", generator="linz2osm")
        self.tree = ElementTree.ElementTree(self.n_root)

        if id_hash is None:
            self._id = 0
        else:
            h = hashlib.sha1(unicode(id_hash).encode('utf8')).hexdigest()
            self._id = -1 * int(h[:6], 16)
    
    def add_feature(self, geom, tags=None):
        self.build_geom(geom, tags)
    
    def xml(self):
        # prettify - ok to run this more than once
        self._etree_indent(self.tree.getroot())
    
        s = StringIO()
        self.tree.write(s, 'utf-8')
        return s.getvalue()
    
    @property
    def next_id(self):
        """ Return a unique ID. """
        self._id -= 1
        return str(self._id)
    
    def build_polygon(self, geom, tags, root=None):
        if not root: 
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
                w_ids = self.build_way(ring.tuple, None)
                for w_id in w_ids:
                    ElementTree.SubElement(r, 'member', type="way", ref=w_id, role=('outer' if (i == 0) else 'inner'))

        if not root:
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
                n_id = node_map.get(c)
                if n_id is None:
                    n_id = self.next_id
                    ElementTree.SubElement(self.n_create, 'node', id=n_id, lat=str(c[1]), lon=str(c[0]))
                    node_map[c] = n_id
                
                ElementTree.SubElement(w, 'nd', ref=n_id)
            self.build_tags(w, tags)
            self.n_create.append(w)
            ids.append(w.get('id'))
            
            if len(rem_coords) < 2:
                break
        
        return ids

    def build_node(self, geom, tags):
        n = ElementTree.SubElement(self.n_create, 'node', id=self.next_id, lat=str(geom.y), lon=str(geom.x))
        self.build_tags(n, tags)
        return [n.get('id')]
    
    def build_geom(self, geom, tags):
        if isinstance(geom, geos.Polygon) and (len(geom) == 1) and (len(geom[0]) <= self.WAY_SPLIT_SIZE):
            # short single-ring polygons are built as ways
            return self.build_way(geom[0].tuple, tags)
            
        elif isinstance(geom, (geos.MultiPolygon, geos.Polygon)):
            return self.build_polygon(geom, tags)
    
        elif isinstance(geom, geos.GeometryCollection):
            # FIXME: Link together as a relation?
            ids = []
            for g in geom:
                ids += self.build_geom(g, tags)
            return ids
        
        elif isinstance(geom, geos.Point):
            # node
            return self.build_node(geom, tags)
        
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

        