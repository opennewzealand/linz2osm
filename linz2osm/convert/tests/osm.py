import unittest

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
    
    def test_node(self):
        w = osm.OSMWriter()
        
        p = geos.Point(123, 456)
        
        id = w.build_node(p, [])
        print w.xml()

        n = w.tree.find('/create/node')
        self.assert_(n is not None, "Couldn't find <node>")
        
        self.assertEqual(len(w.tree.findall('//node')), 1)
        
        self.assert_(int(n.get('id')) < 0, "ID < 0")
        self.assertEqual(float(n.get('lon')), 123)
        self.assertEqual(float(n.get('lat')), 456)
        self.assertEqual(len(n.getchildren()), 0)
