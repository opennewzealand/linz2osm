from django.test import TestCase

from django.contrib.gis import geos

from linz2osm.convert.processing.line_reverse import ReverseLine
    
class TestReverseLine(TestCase):
    def test_simple(self):
        l = geos.LineString(((0,0), (1,1)))
        
        p = ReverseLine()
        l2 = p.handle(l)
        
        self.assertEqual(((1,1), (0,0)), l2.tuple)
