from __future__ import absolute_import

from django.conf import settings
from linz2osm.convert import osm
from linz2osm.workslices.celery import Celery
from datetime import datetime
import time

celery = Celery('tasks', broker = settings.BROKER_URL)

@celery.task
def osm_export(workslice):
    start_t = time.time()
    time.sleep(5)
    data = osm.export(workslice.dataset, workslice.layer, workslice.bounds)
    f = open("%s/%s.osc" % (settings.MEDIA_ROOT, workslice.name), 'w')
    f.write(data)
    f.close()
    workslice.state = 'out'
    workslice.status_changed_at = datetime.now()
    workslice.save()
    finish_t = time.time()
    print "MISSION COMPLETE - generated %s.osc in %f sec" % (workslice.name, finish_t - start_t)
    return workslice
