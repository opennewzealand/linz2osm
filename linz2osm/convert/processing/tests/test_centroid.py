import unittest

from django.contrib.gis import geos

from linz2osm.convert.processing.centroid import Centroid

class TestCentroid(unittest.TestCase):
    def test_simple(self):
        g = geos.Polygon(((0,0), (10,0), (10,10), (0,10), (0,0)))

        p = Centroid()
        g2 = p.handle(g)

        self.assertEqual(g2.geom_type, 'Point')
        self.assertEqual(g2.tuple, (5,5))
