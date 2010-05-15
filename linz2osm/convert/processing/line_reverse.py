from django.contrib.gis import geos

from linz2osm.convert.processing.base import BaseProcessor, Error
    
class ReverseLine(BaseProcessor):
    """ Reverse every line """
    
    geom_types = (geos.LineString, geos.MultiLineString)
    multi_geometries = False
    
    def handle(self, geometry, fields=None, tags=None, id=None):
        if isinstance(geometry, geos.MultiLineString):
            return geos.MultiLinestring(srid=geometry.srid, *[self.handle(g) for g in geometry])
        
        geometry.reverse()
        return geometry
