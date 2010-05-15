import unittest

from django.contrib.gis import geos

from linz2osm.convert.processing.poly_winding import PolyWindingCW, PolyWindingCCW
    
class TestPolyWinding(unittest.TestCase):
    def test_ring_clockwise(self):
        cw = [(0,0), (10,10), (20,0), (0,0)]
        ccw = cw[:]
        ccw.reverse()
        
        p = PolyWindingCCW()
        self.assertEqual(True, p.ring_is_clockwise(cw))
        self.assertEqual(False, p.ring_is_clockwise(ccw))
        
        p = PolyWindingCW()
        self.assertEqual(True, p.ring_is_clockwise(p.wind_ring(cw, is_outer=True)))
        self.assertEqual(True, p.ring_is_clockwise(p.wind_ring(ccw, is_outer=True)))
        self.assertEqual(False, p.ring_is_clockwise(p.wind_ring(cw, is_outer=False)))
        self.assertEqual(False, p.ring_is_clockwise(p.wind_ring(ccw, is_outer=False)))

        p = PolyWindingCCW()
        self.assertEqual(False, p.ring_is_clockwise(p.wind_ring(cw, is_outer=True)))
        self.assertEqual(False, p.ring_is_clockwise(p.wind_ring(ccw, is_outer=True)))
        self.assertEqual(True, p.ring_is_clockwise(p.wind_ring(cw, is_outer=False)))
        self.assertEqual(True, p.ring_is_clockwise(p.wind_ring(ccw, is_outer=False)))

    def test_polygon_orientation_simple(self):
        geoms = {
            "cw" : [(0,0), (10,10), (20,0), (0,0)],
            "ccw" : [(0,0), (20,0), (10,10), (0,0)],
        }

        for dir in ('cw', 'ccw'):
            for name, ring in geoms.items():
                print "layer=%s, data=%s" % (dir, name)
                p = PolyWindingCCW() if (dir == 'ccw') else PolyWindingCW()
                
                g_out = p.handle(geos.Polygon(ring))
                coords = g_out[0].tuple
                
                if dir == 'cw':
                    self.assert_(p.ring_is_clockwise(coords), "Outer-ring coords are anticlockwise (expecting cw)!")
                else:
                    self.assert_(not p.ring_is_clockwise(coords), "Outer-ring coords are clockwise (expecting ccw)!")
    
    def test_polygon_orientation_multipolygon(self):
        geoms = {
            "cw+ccw": ([(0,0), (10,10), (20,0), (0,0)], [(8,2), (12,2), (10,4), (8,2)]),
            "cw+cw": ([(0,0), (10,10), (20,0), (0,0)], [(8,2), (10,4), (12,2), (8,2)]),
            "ccw+cw": ([(0,0), (20,0), (10,10), (0,0)], [(8,2), (10,4), (12,2), (8,2)]),
            "ccw+ccw": ([(0,0), (20,0), (10,10), (0,0)], [(8,2), (12,2), (10,4), (8,2)]),
        }

        for dir in ('cw', 'ccw'):
            for name, rings in geoms.items():
                print "layer=%s, data=%s" % (dir, name)
                p = PolyWindingCCW() if (dir == 'ccw') else PolyWindingCW()
                
                g_out = p.handle(geos.Polygon(*rings))
                for i,mn in enumerate(g_out):
                    coords = g_out[i].tuple
                        
                    if i == 0:
                        if dir == 'cw':
                            self.assert_(p.ring_is_clockwise(coords), "Outer-ring coords are anticlockwise!")
                        else:
                            self.assert_(not p.ring_is_clockwise(coords), "Outer-ring coords are clockwise!")
                    else:
                        if dir == 'cw':
                            self.assert_(not p.ring_is_clockwise(coords), "Inner-ring coords are clockwise!")
                        else:
                            self.assert_(p.ring_is_clockwise(coords), "Inner-ring coords are anticlockwise!")

