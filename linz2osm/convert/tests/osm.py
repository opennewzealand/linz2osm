import unittest
from xml.etree import ElementTree

from django.contrib.gis import geos

from linz2osm.convert import osm

class TestWriter(unittest.TestCase):
    def test_id(self):
        w = osm.OSMWriter()
        
        id0 = w.next_id
        self.assertEqual(type(id0), str)
        self.assert_(int(id0) < 0, "Expected ID <0, got %s" % id0)
        id1 = w.next_id
        self.assert_(int(id1) < 0, "Expected ID <0, got %s" % id0)
        self.assertNotEqual(int(id1), int(id0))

    def test_id_hash(self):
        w = osm.OSMWriter()
        self.assertEqual(int(w.next_id), -1)
        
        w = osm.OSMWriter('bob')
        id = int(w.next_id)
        self.assert_(id < 0, "Expected ID <0, got %s" % id)
        self.assertNotEqual(id, -1)

        w = osm.OSMWriter(777)
        id = int(w.next_id)
        self.assert_(id < 0, "Expected ID <0, got %s" % id)
        self.assertNotEqual(id, -1)

        w = osm.OSMWriter(u'unicode: \xe4\xf6\xfc')
        id = int(w.next_id)
        self.assert_(id < 0, "Expected ID <0, got %s" % id)
        self.assertNotEqual(id, -1)

        w = osm.OSMWriter((7, u'unicode: \xe4\xf6\xfc'))
        id = int(w.next_id)
        self.assert_(id < 0, "Expected ID <0, got %s" % id)
        self.assertNotEqual(id, -1)
    
    def test_node(self):
        w = osm.OSMWriter()
        
        id = w.build_node(geos.Point(123, 456), [])
        print w.xml()

        n = w.tree.find('/create/node')
        self.assert_(n is not None, "Couldn't find <node>")
        self.assertEqual(n.get('id'), id)
        
        self.assertEqual(len(w.tree.findall('//node')), 1)
        
        self.assert_(int(n.get('id')) < 0, "ID < 0")
        self.assertEqual(float(n.get('lon')), 123)
        self.assertEqual(float(n.get('lat')), 456)
        self.assertEqual(len(n.getchildren()), 0)

        id = w.build_node(geos.Point(234, 567), [])
        self.assertEqual(len(w.tree.findall('//node')), 2)
    
    def test_tags_single(self):
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')
        
        w.build_tags(parent, {'t1': 'v1'})
        self.assertEqual(len(parent.getchildren()), 1)
        tn = parent.getchildren()[0]
        self.assertEqual(tn.tag, 'tag')
        self.assertEqual(tn.get('k'), 't1')
        self.assertEqual(tn.get('v'), 'v1')
    
    def test_tags_empty(self):
        # should be able to call with empty dicts
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')

        w.build_tags(parent, {})
        w.build_tags(parent, None)
        
    def test_tags_multiple(self):
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')
        w.build_tags(parent, {'t0': 'v0', 't1': 'v1'})
        self.assertEqual(len(parent.getchildren()), 2)
        for i,tn in enumerate(parent.getchildren()):
            self.assertEqual(tn.tag, 'tag')
            self.assertEqual(tn.get('k'), 't%d' % i)
            self.assertEqual(tn.get('v'), 'v%d' % i)
        
    def test_tags_unicode(self):
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')
        w.build_tags(parent, {u'unicode_tag: \xe4\xf6\xfc': u'unicode_value: \xe4\xf6\xfc'})
        tn = parent.getchildren()[0]
        self.assertEqual(tn.get('k'), u'unicode_tag: \xe4\xf6\xfc')
        self.assertEqual(tn.get('v'), u'unicode_value: \xe4\xf6\xfc')
    
    def test_tags_nonstring(self):
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')
        w.build_tags(parent, {'t1': 7})
        tn = parent.getchildren()[0]
        self.assertEqual(tn.get('v'), '7')

    def test_tags_long(self):
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')
        self.assertRaises(osm.Error, w.build_tags, parent, {'*' * 256: 'v'})
        self.assertRaises(osm.Error, w.build_tags, parent, {'t': '*' * 256})

    def test_way_simple(self):
        w = osm.OSMWriter()

        l = ((1,1), (2,2), (3,3),)

        id = w.build_way(l, {})
        print w.xml()
        
        n = w.tree.find('/create/way')
        self.assert_(n is not None, "Couldn't find <way>")
        
        self.assertEqual(len(w.tree.findall('//way')), 1)

        nodes = w.tree.findall('/create/node') 
        self.assertEqual(len(nodes), 3)
        node_map = dict([(nn.get('id'), nn) for nn in nodes])
        
        self.assert_(int(n.get('id')) < 0, "ID < 0")
        self.assertEqual(n.get('id'), id)
        self.assertEqual(len(n.getchildren()), 3)
        for i in range(3):
            nc = n.getchildren()[i]
            self.assertEqual(nc.tag, 'nd')
            node_ref = nc.get('ref')
            self.assert_(node_ref)
            node_el = node_map.get(node_ref)
            self.assert_(node_el is not None)
            self.assertEqual(float(node_el.get('lon')), l[i][0])
            self.assertEqual(float(node_el.get('lat')), l[i][1])
    
    def test_way_multiple(self):
        w = osm.OSMWriter()

        l = (
            ((1,1), (2,2), (3,3),),
            ((2,2), (3,3), (4,4),),
        )

        ids = (
            w.build_way(l[0], {}),
            w.build_way(l[1], {}),
        )
        print w.xml()
        
        ways = w.tree.findall('/create/way')
        self.assertEqual(len(w.tree.findall('//way')), 2)

        nodes = w.tree.findall('/create/node') 
        self.assertEqual(len(nodes), 6)
        node_map = dict([(nn.get('id'), nn) for nn in nodes])
        
        for j,wn in enumerate(ways):
            self.assertEqual(len(wn.getchildren()), 3)
            for i in range(3):
                nc = wn.getchildren()[i]
                self.assertEqual(nc.tag, 'nd')
                node_ref = nc.get('ref')
                self.assert_(node_ref)
                node_el = node_map.get(node_ref)
                self.assert_(node_el is not None)
                self.assertEqual(float(node_el.get('lon')), l[j][i][0])
                self.assertEqual(float(node_el.get('lat')), l[j][i][1])
    
    def test_way_circular(self):
        w = osm.OSMWriter()

        l = ((0,0), (1,1), (2,0), (0,0),)

        id = w.build_way(l, {})
        print w.xml()
        
        wn = w.tree.find('/create/way')
        nodes = w.tree.findall('/create/node') 
        self.assertEqual(len(nodes), 3) # not 4!
        node_map = dict([(nn.get('id'), nn) for nn in nodes])
        
        self.assertEqual(len(wn.getchildren()), 4)
        for i,nc in enumerate(wn.getchildren()):
            node_ref = nc.get('ref')
            node_el = node_map.get(node_ref)
            self.assert_(node_el is not None)
        
        self.assertEqual(wn.getchildren()[0].get('ref'), wn.getchildren()[3].get('ref'))

    def test_way_crossover(self):
        w = osm.OSMWriter()

        l = ((0,0), (1,1), (2,0), (0,0), (-1,-1),)

        id = w.build_way(l, {})
        print w.xml()
        
        wn = w.tree.find('/create/way')
        nodes = w.tree.findall('/create/node') 
        self.assertEqual(len(nodes), 4) # not 4!
        node_map = dict([(nn.get('id'), nn) for nn in nodes])
        
        self.assertEqual(len(wn.getchildren()), 5)
        for i,nc in enumerate(wn.getchildren()):
            node_ref = nc.get('ref')
            node_el = node_map.get(node_ref)
            self.assert_(node_el is not None)
        
        self.assertEqual(wn.getchildren()[0].get('ref'), wn.getchildren()[3].get('ref'))
    
    def test_way_split(self):
        #TODO
        w = osm.OSMWriter()
        
        l = [(x, -x) for x in range(4500)]
        self.assertRaises(osm.Error, w.build_way, l, {})
    
    def test_geom(self):
        geoms = (
        #   #nodes, #ways, #relations, #tags, geom
            (1, 0, 0, 1, geos.Point(0,0) ),
            (2, 1, 0, 1, geos.LineString([(0,0), (1,1)]) ),
            # polygons with a single ring are written as circular ways
            (3, 1, 0, 1, geos.Polygon([(0,0), (1,1), (2,0), (0,0)]) ),
            # otherwise they're written as relations
            # multipolygon relations have an extra tag
            (6, 2, 1, 1+1, geos.Polygon([(0,0), (10,10), (20,0), (0,0)], [(8,2), (10,4), (12,2), (8,2)]) ),
            (2, 0, 0, 2, geos.MultiPoint(geos.Point(0,0), geos.Point(10,10)) ),
            (4, 2, 0, 2, geos.MultiLineString(
                geos.LineString([(0, 0), (1, 1)]), 
                geos.LineString([(10,10), (11,11)]) )),
            (9, 3, 1, 1+1, geos.MultiPolygon(
                geos.Polygon([(0,0), (1,1), (2,0), (0,0)]),
                geos.Polygon([(0,0), (10,10), (20,0), (0,0)], [(8,2), (10,4), (12,2), (8,2)]) )),
            (3, 1, 0, 2, geos.GeometryCollection(
                geos.Point(0,0),
                geos.LineString([(0,0), (1,1)]) )),
        )
        
        for i, (node_count, way_count, relation_count, tag_count, geom) in enumerate(geoms):
            w = osm.OSMWriter()
            
            print "#%d: %s" % (i, geom.wkt)
            w.build_geom(geom, {'mytag':'myvalue'})
            print w.xml()
            
            self.assertEqual(len(w.tree.findall('/create/node')), node_count)
            self.assertEqual(len(w.tree.findall('/create/way')), way_count)
            self.assertEqual(len(w.tree.findall('/create/relation')), relation_count)
            self.assertEqual(len(w.tree.findall('//tag')), tag_count)
        


        