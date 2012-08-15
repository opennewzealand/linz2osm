from django.core.management.base import BaseCommand

from linz2osm.workslices.models import Workslice
from linz2osm.workslices import tasks

class Command(BaseCommand):
    help = "Restarts processing of workslices if interrupted"

    def handle(self, *args, **options):
        for workslice in Workslice.objects.filter(state='processing').all():
            tasks.osm_export.delay(workslice)
            print "Restarting processing on workslice #%d" % workslice.id

            
