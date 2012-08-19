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

from django.core.management.base import BaseCommand
from django.db import transaction, connection, connections
    
class Command(BaseCommand):
    help = "Alter character columns to character varying"

    def handle(self, **options):
        for conn_name in connections:
            if conn_name != 'default':
                conn = connections[conn_name]
                cursor = conn.cursor()
                cursor.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public' AND data_type = 'character';")
                char_columns = cursor.fetchall()

                print
                print "----"
                print conn_name
                print "----"
                
                for table_name, column_name in char_columns:
                    print "ALTER TABLE %s ALTER COLUMN %s SET DATA TYPE character varying;" % (table_name, column_name)