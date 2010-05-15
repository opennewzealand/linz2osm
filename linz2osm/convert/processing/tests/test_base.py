import unittest

from django.contrib.gis import geos

from linz2osm.convert.processing.base import BaseProcessor

class TestBaseProcessor(unittest.TestCase):
    def test_multi(self):
        l = geos.LineString((0,0), (1,1))
        ml = geos.MultiLineString(l, l)
        
        g = []
        class T(BaseProcessor):
            multi_geometries=True
            
            def handle(self, geometry, fields=None, tags=None, id=None):
                g.append(geometry)
                return geometry
        
        p = T()

        p.process(l)
        self.assert_(isinstance(g[0], geos.LineString))

        g = []
        p.process(ml)
        self.assert_(isinstance(g[0], geos.MultiLineString))
        
        p.multi_geometries = False
        g = []
        p.process(l)
        self.assert_(isinstance(g[0], geos.LineString))

        g = []
        p.process(ml)
        self.assertEqual(len(g), 2)
        self.assert_(isinstance(g[0], geos.LineString))
        self.assert_(isinstance(g[1], geos.LineString))
