from xml.etree import ElementTree
from cStringIO import StringIO

from django.db import connections
from django.conf import settings
from django.contrib.gis import geos
from django.utils import simplejson

class Error(Exception):
    pass

def get_layer_datasets(layer):
    db = []
    for ds_id, ds_info in settings.DATABASES.items():
        if ds_id == 'default':
            continue
        if has_layer(ds_id, layer):
            db.append((ds_id, ds_info.get('_description', ds_id),))
    return db

def has_layer(database_id, layer):
    cursor = connections[database_id].cursor()
    cursor.execute('SELECT count(*) FROM information_schema.tables WHERE table_name=%s;', [layer.name])
    count = cursor.fetchone()[0]
    return (count == 1)

def dataset_tables(database_id):
    cursor = connections[database_id].cursor()
    cursor.execute('SELECT table_name FROM information_schema.tables;')
    return [r[0] for r in cursor]

def export(database_id, layer, bbox=None):
    e = _Export(database_id, layer, bbox)
    s = StringIO()
    e.tree.write(s, 'utf-8')
    return s.getvalue()

class _Export(object):
    def __init__(self, database_id, layer, bbox=None):
        
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
        
        n_root = ElementTree.Element('osmChange', version="0.6", generator="linz2osm")
        self.n_create = ElementTree.SubElement(n_root, 'create', version="0.6", generator="linz2osm")
        
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
            
            self._build_geom(row_geom, row_tags)
        
        self.tree = ElementTree.ElementTree(n_root)
    
    @property
    def _next_id(self):
        if not hasattr(self, '_id'):
            self._id = 0
        
        self._id -= 1
        return str(self._id)
    
    def _build_polygon(self, geom, tags, root=None):
        if not root: 
            r = ElementTree.Element('relation', id=self._next_id)
            ElementTree.SubElement(r, 'tag', k='type', v='multipolygon')
            self._build_tags(r, tags)
        else:
            r = root
        
        if isinstance(geom, geos.MultiPolygon):
            for g in geom:
                self._build_polygon(g, tags, r)
        else:
            for i,ring in enumerate(geom):
                w_id = self._build_way(ring.tuple, None, True)
                ElementTree.SubElement(r, 'member', type="way", ref=w_id, role=('outer' if (i == 0) else 'inner'))

        if not root:
            self.n_create.append(r)
        return r.get('id')
            
    def _build_way(self, coords, tags, poly=False):
        assert len(coords) <= 2000, "Too many nodes in a way: splitting is unsupported!"
        
        w = ElementTree.Element('way', id=self._next_id)
        n_id_0 = self._next_id
        n_id = n_id_0
        for i,(cx,cy) in enumerate(coords):
            if i == (len(coords)-1):
                n_id = n_id_0
            else:
                ElementTree.SubElement(self.n_create, 'node', id=n_id, lat=str(cy), lon=str(cx))
            ElementTree.SubElement(w, 'nd', ref=n_id)
            n_id = self._next_id
        self._build_tags(w, tags)
        self.n_create.append(w)
        return w.get('id')
    
    def _build_geom(self, geom, tags):
        if isinstance(geom, (geos.MultiPolygon, geos.Polygon)):
            self._build_polygon(geom, tags)
    
        elif isinstance(geom, geos.GeometryCollection):
            for g in geom:
                self._build_geom(g, tags)
        
        elif isinstance(geom, geos.Point):
            # node
            n = ElementTree.SubElement(self.n_create, 'node', id=self._next_id, lat=str(geom.y), lon=str(geom.x))
            self._build_tags(n, tags)
            n.get('id')
        
        elif isinstance(geom, geos.LineString):
            # way
            self._build_way(geom.tuple, tags)
        
    def _build_tags(self, parent_node, tags):
        if tags:
            for tn,tv in tags.items():
                ElementTree.SubElement(parent_node, 'tag', k=tn, v=str(tv))
