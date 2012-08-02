from __future__ import absolute_import

from django.conf import settings
from linz2osm.convert import osm
from linz2osm.workslices.celery import Celery
from datetime import datetime
import time
import os.path

celery = Celery('tasks', broker = settings.BROKER_URL)

@celery.task
def osm_export(workslice):
    start_t = time.time()
    data = osm.export(workslice.layer_in_dataset.dataset.name, workslice.layer_in_dataset.layer)

    filepath = "%s/%s.osc" % (settings.MEDIA_ROOT, workslice.name)
    f = open(filepath, 'w')
    f.write(data)
    f.close()
    
    workslice.state = 'out'
    workslice.status_changed_at = datetime.now()
    workslice.file_size = os.path.getsize(filepath)
    workslice.save()
    finish_t = time.time()
    print "MISSION COMPLETE - generated %s.osc (%d bytes) in %f sec" % (workslice.name, workslice.file_size, finish_t - start_t)
    return workslice
