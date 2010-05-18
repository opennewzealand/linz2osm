from linz2osm.convert.processing.base import Error
from linz2osm.convert.processing.river_direction import RiverDirection
from linz2osm.convert.processing.line_reverse import ReverseLine
from linz2osm.convert.processing.poly_winding import PolyWindingCW, PolyWindingCCW
from linz2osm.convert.processing.centroid import Centroid

def get_available():
    import inspect
    from linz2osm.convert import processing as m
    from linz2osm.convert.processing.base import BaseProcessor
    
    avail = {}
    for k in dir(m):
        o = getattr(m, k)
        if inspect.isclass(o) and issubclass(o, BaseProcessor):
            avail[k] = (o.__doc__ or k).strip()
    
    return avail

def get_class(key):
    from linz2osm.convert import processing as m
    c = getattr(m, key, None)
    if not c:
        raise Error("Unknown Processor: %s" % key)
    else:
        return c
