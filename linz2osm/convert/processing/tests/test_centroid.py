import unittest

from django.contrib.gis import geos

from linz2osm.convert.processing.centroid import PointOnSurface

class TestCentroid(unittest.TestCase):
    def test_simple(self):
        g = geos.Polygon(((0,0), (10,0), (10,10), (0,10), (0,0)))

        p = Centroid()
        g2 = p.handle(g)

        self.assertEqual(g2.geom_type, 'Point')
        self.assertEqual(g2.tuple, (5,5))

class TestPointOnSurface(unittest.TestCase):
    def test_poly_square(self):
        g = geos.Polygon(((0,0), (10,0), (10,10), (0,10), (0,0)))

        p = PointOnSurface()
        g2 = p.handle(g)

        self.assertEqual(g2.geom_type, 'Point')
        self.assert_(g2.intersects(g))
        self.assertEqual(g2.tuple, (5,5))

    def test_poly_n(self):
        g = geos.Polygon(((0,0), (2,0), (2,8), (8,8), (8,0), (10,0), (10,10), (0,10), (0,0)))

        p = PointOnSurface()
        g2 = p.handle(g)

        self.assertEqual(g2.geom_type, 'Point')
        self.assert_(g2.intersects(g))

    def test_line(self):
        g = geos.LineString((0,0), (0,10), (10,10))

        p = PointOnSurface()
        g2 = p.handle(g)

        self.assertEqual(g2.geom_type, 'Point')
        self.assert_(g2.tuple in g.tuple)
