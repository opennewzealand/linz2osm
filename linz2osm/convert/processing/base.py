from django.contrib.gis import geos

class Error(Exception):
    pass

class BaseProcessor(object):
    geom_types = None
    multi_geometries = True # can handle multi-geometries. False == process each component

    def __init__(self):
        self.warnings = []
        
    def warn(self, message, id=None):
        if id:
            message = "%s: %s" % (id, message)
        self.warnings.append(message)
    
    def process(self, geometry, fields=None, tags=None, id=None):
        if geometry is None:
            return None
        
        if self.geom_types:
            if not isinstance(geometry, self.geom_types):
                raise Error("Invalid geometry type: %s" % geometry.geom_type) 
        
        if (not self.multi_geometries) and isinstance(geometry, geos.GeometryCollection):
            return geometry.__class__(srid=geometry.srid, *[self.handle(g) for g in geometry])
        else:
            return self.handle(geometry, fields, tags, id)
        
    def handle(self, geometry, fields=None, tags=None, id=None):
        """ Subclasses override to provide functionality. """
        pass
