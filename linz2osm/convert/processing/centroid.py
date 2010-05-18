from linz2osm.convert.processing.base import BaseProcessor

class Centroid(BaseProcessor):
    """
    Return the centroid of the geometry.
    """

    def handle(self, geometry, fields=None, tags=None, id=None):
        return geometry.centroid
