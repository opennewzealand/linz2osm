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
