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

from django.test import TestCase
from linz2osm.data_dict.models import Dataset, LayerInDataset, Layer, Tag

class TagFetchingTestCase(TestCase):
    fixtures = ['data_dict_test.json']
    
    def setUp(self):
        self.mainland = Dataset.objects.get(pk='mainland')
        self.kermadecs = Dataset.objects.get(pk='kermadec_is')
        self.nzopengps = Dataset.objects.get(pk='opengps_mainland')
        self.cave_pnt = Layer.objects.get(pk='cave_pnt')
        self.pipeline_cl = Layer.objects.get(pk='pipeline_cl')
        self.nzopengps_road = Layer.objects.get(pk='nzopengps_road')

    def test_get_all_tags_for_layer(self):
        # FIXME use objects, not IDs
        
        cave_pnt_tags = self.cave_pnt.get_all_tags()
        self.assertEqual(len(cave_pnt_tags), 4)
        self.assertItemsEqual([t.id for t in cave_pnt_tags], [1, 2, 6, 8])

        pipeline_cl_tags = self.pipeline_cl.get_all_tags()
        self.assertEqual(len(pipeline_cl_tags), 4)
        self.assertItemsEqual([t.id for t in pipeline_cl_tags], [3, 4, 6, 7])

        nzopengps_road_tags = self.nzopengps_road.get_all_tags()
        self.assertEqual(len(nzopengps_road_tags), 3)
        self.assertItemsEqual([t.id for t in nzopengps_road_tags], [5, 6, 7])
