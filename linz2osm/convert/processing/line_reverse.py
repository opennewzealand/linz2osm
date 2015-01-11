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

from django.contrib.gis import geos

from linz2osm.convert.processing.base import BaseProcessor, Error

class ReverseLine(BaseProcessor):
    """
    Reverse all the coordinate sequences.
    Only applies to line layers.
    Use with care, you need to manually check coordinate order first!
    Args: None
    """

    geom_types = (geos.LineString, geos.MultiLineString)
    multi_geometries = False

    def handle(self, geometry, fields=None, tags=None, id=None):
        if isinstance(geometry, geos.MultiLineString):
            return geos.MultiLinestring(srid=geometry.srid, *[self.handle(g) for g in geometry])

        geometry.reverse()
        return geometry
