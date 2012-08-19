#  LINZ-2-OSM
#  Copyright (C) 2010-2012 Koordinates Ltd.
# 
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib.gis import geos

from linz2osm.convert.processing.base import BaseProcessor, Error
    
class PolyWindingCW(BaseProcessor):
    """ 
    Re-wind outer polygon rings clockwise. Inner rings are wound the opposite direction. 
    Only applies to polygon layers. 
    Args: None
    """
    
    geom_types = (geos.Polygon, geos.MultiPolygon)
    multi_geometries = False
    cw = True
    
    def handle(self, geometry, fields=None, tags=None, id=None):
        rings = list(geometry.tuple)
        for i in range(len(rings)):
            rings[i] = self.wind_ring(rings[i], i==0)
        
        return geos.Polygon(srid=geometry.srid, *rings)

    def ring_is_clockwise(self, p):
        """
        Returns True if the points in the given ring are in clockwise order,
        or False if they are in anticlockwise order. Calculates a cross product. 
        """
        clen = len(p) - 1
        assert clen >= 3
        total = 0
        for i in xrange(clen):
            x1, y1 = p[i]
            x2, y2 = p[(i + 1) % clen]
            x3, y3 = p[(i + 2) % clen]
            
            # A good cross product tutorial: http://www.netcomuk.co.uk/~jenolive/vect8.html
            
            # We have two vectors U and V such that U = (x2-x1, y2-y1), V = (x3-x2, y3-y2)
            # The cross product `U X V` of 2d vectors is given by UxVy - UyVx
            
            dx1 = x2 - x1
            dy1 = y2 - y1
            dx2 = x3 - x2
            dy2 = y3 - y2
            
            cp = dx1*dy2 - dy1*dx2
            
            # That cross product tells us the angular directionality of the corner 
            # defined by our two vectors U,V (negative means clockwise)
            
            # now we have a vector in the Z dimension with magnitude |U| * |V| * sin(theta)
            # where theta is the angle between U and V
            
            # get vector magnitudes
            u = float(dx1**2 + dy1**2)**0.5
            v = float(dx2**2 + dy2**2)**0.5
            
            # so now if we divide by the length of the vectors, we get sin(theta)
            # adding the sin'd thetas gives us a -ve number for clockwise or +ve for anticlockwise
            try:
                total += cp / (u*v)
            except ZeroDivisionError:
                # if the data is horrible and has concurrent points, we can just skip this calculation
                continue
        return (total <= 0)

    def wind_ring(self, ring, is_outer):
        if self.cw:
            wind_cw = is_outer
        else:
            wind_cw = not is_outer
        
        if self.ring_is_clockwise(ring) != wind_cw:
            ring = list(ring)
            ring.reverse()
        return ring

class PolyWindingCCW(PolyWindingCW):
    """ 
    Re-wind outer polygon rings anti-clockwise (default for OSM). 
    Inner rings are wound the opposite direction. 
    Only applies to polygon layers. 
    Args: None
    """
    cw = False
