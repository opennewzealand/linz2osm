import os.path

from django.core.management.base import LabelCommand
from django.core.management.color import no_style
from django.contrib.gis.utils import LayerMapping
from django.conf import settings
from django.db import connection

from linz2osm.boundaries.models import Boundary

class Command(LabelCommand):
    help = "Loads Stats NZ boundaries"
    args = "<shapefile_dir>"
    label = "shapefile_dir"

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

    def handle(self, shapefile_dir, **options):
        self.style = no_style()
        
        # otherwise we log a shitload
        settings.DEBUG = False
        
        print "Deleting old boundaries..."
        Boundary.objects.all().delete()
        
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
            
            print "Simplifying geometries"
            curs = connection.cursor()
            # 0.0032 degress == ~250m
            curs.execute("UPDATE boundaries_boundary SET poly=ST_Simplify(poly, 0.0032) WHERE level=%s AND NOT ST_IsEmpty(ST_Simplify(poly, 0.0032));", [level])
            
        print "All Done :)"
