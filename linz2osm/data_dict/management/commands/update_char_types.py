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

                for table_name, column_name in char_columns:
                    cursor.execute("ALTER TABLE %s ALTER COLUMN %s SET DATA TYPE character varying;" % (table_name, column_name))
                    print "%s : %s.%s" % (conn_name, table_name, column_name)
