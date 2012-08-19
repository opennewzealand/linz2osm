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
from django.db import connections

from linz2osm.convert.processing.base import BaseProcessor, Error
    
class RiverDirection(BaseProcessor):
    """ 
    Query a DEM to order river coordinates to match flow direction.
    Args: db, table, [srid, tolerance, elevation_field, geom_field]
    """
    
    geom_types = (geos.LineString, geos.MultiLineString)
    multi_geometries = False
    
    def __init__(self, db, table, srid=2193, tolerance=500, elevation_field='elevation', geom_field='wkb_geometry'):
        self.db = db
        self.table = table
        self.srid = srid
        self.tolerance = tolerance
        self.geom_field = geom_field
        self.elev_field = elevation_field
        
    def handle(self, geometry, fields=None, tags=None, id=None):
        start = geometry[0]
        end = geometry[1]
        
        if self.srid != geometry.srid:
            start.transform(self.srid)
            end.transform(self.srid)
        
        elev_start = self.get_elevation(start)
        elev_end = self.get_elevation(end)
        
        if elev_start is not None and elev_end is not None:
            if elev_end > elev_start:
                geometry.reverse()
        else:
            self.warn("Couldn't get start/end elevation: %s/%s" % (elev_start, elev_end), id)
        
        return geometry
        
    def get_elevation(self, point):
        cursor = connections[self.db].cursor()
        sql = ( 'SELECT %(elev_field)s '
                'FROM %(table)s '
                'WHERE st_dwithin(%(geom_field)s, %%s, %%s) '
                'ORDER BY st_distance(%(geom_field)s, %%s) '
                'LIMIT 1;') % {'elev_field': self.elev_field, 'geom_field':self.geom_field}
                
        cursor.execute(sql, [point.hexewkb, self.tolerance, point.hexewkb])
        r = cursor.fetchone()
        if r is not None:
            return float(r[0])
        else:
            return None
