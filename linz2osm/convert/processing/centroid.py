from linz2osm.convert.processing.base import BaseProcessor

class Centroid(BaseProcessor):
    """
    Return the centroid of the geometry (this may not actually overlap it!)
    """

    def handle(self, geometry, fields=None, tags=None, id=None):
        return geometry.centroid

class PointOnSurface(BaseProcessor):
    """
    Return a point guaranteed to be on the line/surface, and somewhere near the middle.
    """

    def handle(self, geometry, fields=None, tags=None, id=None):
        return geometry.point_on_surface
