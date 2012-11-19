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
    print "DOING DATASET UPDATE"
    start_t = time.time()
    dataset_update.run()
    finish_t = time.time()
    print "MISSION COMPLETE - updated %s in %f sec" % (dataset_update.dataset.name, finish_t - start_t)

@celery.task
def deletions_export(dataset):
    print "EXPORTING DELETE SET"
    start_t = time.time()

    try:
        layers_in_dataset = dataset.layerindataset_set.all()
        for lid in layers_in_dataset:
            nodes = []
            ways = []
            relations = []
        
            matches = osm.featureset_matches(lid, lid.workslicefeature_set.filter(dirty=1))
            for (wf, osm_results) in matches:
                for elem in osm_results['elements']:
                    if elem['type'] == 'node':
                        nodes.append(elem)
                    elif elem['type'] == 'way':
                        ways.append(elem)
                    elif elem['type'] == 'relation':
                        relations.append(elem)
                    else:
                        raise osm.Error("Unsupported element type %s" % elem['type'])
            
            data = osm.export_delete(lid, nodes, ways, relations)        
            filename = lid.export_deletes_name()
        
            filepath = "%s/%s.osc" % (settings.MEDIA_ROOT, filename)
            f = open(filepath, 'w')
            f.write(data)
            f.close()

            lid.last_deletions_dump_filename = filename
            lid.save()
            print "For %s - generated %s.osc" % (lid.layer_id, filename)
    except:
        raise
    finally:
        dataset.generating_deletions_osm = False
        dataset.save()
        
    finish_t = time.time()
    print "MISSION COMPLETE - generated %d layers in %f sec" % (len(layers_in_dataset), finish_t - start_t) 
