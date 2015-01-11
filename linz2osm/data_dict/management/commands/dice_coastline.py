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

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry, LineString
from django.db import connections, transaction

SPLIT_THRESHOLD = 950
SPLIT_AMOUNT = 900
DB_NAME = 'mainland'

@transaction.commit_manually(using=DB_NAME)
class Command(BaseCommand):
    help = "Chops the mainland coastline up into sub-1000 node chunks"

    def handle(self, **options):
        c = connections[DB_NAME].cursor()
        c.execute("DELETE FROM coastline WHERE ogc_fid >= 1000000;")
        transaction.commit(using=DB_NAME)
        c.execute("SELECT ogc_fid, wkb_geometry, elevation FROM coastline ORDER BY ogc_fid;")
        for row in c.fetchall():
            src_fid = row[0]
            src_geom = GEOSGeometry(row[1])
            src_elevation = row[2]
            print "OGC_FID: % 5d - VERTICES: % 8d" % (row[0], src_geom.num_points,)

            if src_geom.num_points > SPLIT_THRESHOLD:
                for start in range(0, src_geom.num_points, SPLIT_AMOUNT):
                    new_fid = src_fid * 1000000 + start
                    new_geom = LineString(src_geom[start:start + SPLIT_AMOUNT + 1])
                    new_geom.srid = src_geom.srid
                    c.execute("INSERT INTO coastline (ogc_fid, wkb_geometry, elevation) VALUES (%d, '%s', %f)" % (new_fid, new_geom.hexewkb, src_elevation))
                    c.execute("DELETE FROM coastline WHERE ogc_fid = %d;" % (src_fid))
                    transaction.commit(using=DB_NAME)
                    print "  * SPLIT INTO OGC_FID: % 10d - VERTICES: % 8d" % (new_fid, new_geom.num_points)

