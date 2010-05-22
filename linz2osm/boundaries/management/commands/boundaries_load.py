import os.path
import sys

from django.core.management.base import BaseCommand, CommandError, make_option
from django.core.management.color import no_style
from django.contrib.gis.utils import LayerMapping
from django.conf import settings
from django.db import connection, transaction

from linz2osm.boundaries.models import Boundary

class Command(BaseCommand):
    help = "Loads Stats NZ boundaries"
    args = "<shapefile_dir>"
    label = "shapefile_dir"

    option_list = list(BaseCommand.option_list) + [
        make_option('--update-only', action='store_true', 
            default=False, dest='update_only',
            help='Update relations on existing boundaries'),
    ]
    
    _mappings = (
        (3, 'AU06_LV2.shp', {
            'name': 'AU_NAME',
            'poly': 'POLYGON',
        }),
        (2, 'UA06_LV2.shp', {
            'name': 'UA_NAME',
            'poly': 'POLYGON',
        }),
        (1, 'TA06_LV2_V2.shp', {
            'name': 'TA_NAME',
            'poly': 'POLYGON',
        }),
        (0, 'REGC06_LV2.shp', {
            'name': 'REGC_NAME',
            'poly': 'POLYGON',
        }),
    )
    
    @transaction.commit_on_success
    def update_relations(self, level):
        b_count = Boundary.objects.filter(level=level).count()
        print >>sys.stderr, "Updating relations between %d boundaries... (level %d)" % (b_count, level)
        for i,b in enumerate(Boundary.objects.filter(level=level)):
            print >>sys.stderr, "%s ..." % b
            try:
                b.update_poly_display()
            except Exception, e:
                print >>sys.stderr, '\tERROR - poly: ', e
                self.errors.append((b.id, str(b), 'poly', e))

            try:
                b.update_children()
            except Exception, e:
                print >>sys.stderr, '\tERROR - children: ', e
                self.errors.append((b.id, str(b), 'children', e))

            try:
                b.update_neighbours()
            except Exception, e:
                print >>sys.stderr, '\tERROR - neighbours: ', e
                self.errors.append((b.id, str(b), 'neighbours', e))

            b.save() 

    def handle(self, *args, **options):
        self.style = no_style()

        if len(args) != 1:
            raise CommandError('Enter the path to the shapefiles.')
        shapefile_dir = args[0]
        
        # otherwise we log a shitload
        settings.DEBUG = False
        
        if not options['update_only']:
            print "Deleting old boundaries..."
            Boundary.objects.defer('poly', 'poly_display').all().delete()
            
            for level, file, mapping in self._mappings:
                print "%s ..." % file
                shp_path = os.path.join(shapefile_dir, file)
                if not os.path.exists(shp_path):
                    self.style.ERROR("Can't find %s" % shp_path)
                    return
                
                # override default
                Boundary._meta.get_field('level').default = level
                
                lm = LayerMapping(Boundary, shp_path, mapping)
                lm.save(verbose=True)
        
        self.errors = []
        for level, file, mapping in reversed(self._mappings):
            self.update_relations(level)
        
        print "All Done :)"
        
        if len(self.errors):
            print "\nERRORS: (%d)" % len(self.errors)
            for b_id, b_str, what, e in self.errors:
                print "%s - %s: %s - %s" % (b_id, b_str, what, e)
