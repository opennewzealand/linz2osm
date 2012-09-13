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
from linz2osm.data_dict.models import Dataset, LayerInDataset, Layer, Tag, Group

class TagFetchingTestCase(TestCase):
    fixtures = ['data_dict_test.json']
    
    def setUp(self):
        self.grp_linz = Group.objects.get(pk='linz')
        self.grp_nzopengps = Group.objects.get(pk='nzopengps')
        self.grp_pipelines = Group.objects.get(pk='pipelines')
        
        self.ds_kermadecs = Dataset.objects.get(pk='kermadec_is')
        self.ds_mainland = Dataset.objects.get(pk='mainland')
        self.ds_nzopengps = Dataset.objects.get(pk='opengps_mainland')
        
        cave_pnt = Layer.objects.get(pk='cave_pnt')
        pipeline_cl = Layer.objects.get(pk='pipeline_cl')
        nzopengps_road = Layer.objects.get(pk='nzopengps_road')

        self.cave_pnt_in_kermadecs = LayerInDataset.objects.get(layer=cave_pnt, dataset=self.ds_kermadecs)
        self.pipeline_cl_in_mainland = LayerInDataset.objects.get(layer=pipeline_cl, dataset=self.ds_mainland)
        self.nzopengps_road_in_mainland = LayerInDataset.objects.get(layer=nzopengps_road, dataset=self.ds_nzopengps)

    def test_group_structure(self):
        self.assertEqual(self.ds_kermadecs.group, self.grp_linz)
        self.assertEqual(self.ds_mainland.group, self.grp_linz)
        self.assertEqual(self.ds_nzopengps.group, self.grp_nzopengps)
        self.assertEqual(self.pipeline_cl_in_mainland.layer.group, self.grp_pipelines)

    def test_get_all_tags_for_layer(self):
        # FIXME use objects, not IDs
        pipeline_cl_tags = self.pipeline_cl_in_mainland.get_all_tags()
        self.assertEqual(len(pipeline_cl_tags), 6)
        self.assertItemsEqual([t.id for t in pipeline_cl_tags], [3, 4, 6, 7, 9, 12])

        cave_pnt_tags = self.cave_pnt_in_kermadecs.get_all_tags()
        self.assertEqual(len(cave_pnt_tags), 6)
        self.assertItemsEqual([t.id for t in cave_pnt_tags], [1, 2, 6, 8, 10, 12])

        nzopengps_road_tags = self.nzopengps_road_in_mainland.get_all_tags()
        self.assertEqual(len(nzopengps_road_tags), 4)
        self.assertItemsEqual([t.id for t in nzopengps_road_tags], [5, 6, 7, 11])
