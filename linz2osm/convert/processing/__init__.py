#  LINZ-2-OSM
#  Copyright (C) Koordinates Ltd.
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

from linz2osm.convert.processing.base import Error
from linz2osm.convert.processing.river_direction import RiverDirection
from linz2osm.convert.processing.line_reverse import ReverseLine
from linz2osm.convert.processing.poly_winding import PolyWindingCW, PolyWindingCCW
from linz2osm.convert.processing.centroid import Centroid, PointOnSurface

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
