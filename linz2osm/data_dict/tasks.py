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

from __future__ import absolute_import

from django.conf import settings
from linz2osm.convert import osm
from linz2osm.workslices.celery import Celery
from datetime import datetime
import time
import os.path

celery = Celery('tasks', broker = settings.BROKER_URL)

@celery.task
def dataset_update(dataset_update):
    start_t = time.time()
    dataset_update.run()
    finish_t = time.time()
    print "MISSION COMPLETE - updated %s in %f sec" % (dataset_update.dataset.name, finish_t - start_t)
