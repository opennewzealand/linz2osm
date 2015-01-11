#  LINZ-2-OSM
#  Copyright (C) Koordinates Ltd.
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

from django.contrib.auth.models import User
from django.contrib.gis import geos
from django.db import connections
from django.test import TestCase
from linz2osm.convert import osm
from linz2osm.data_dict.models import *
from linz2osm.workslices.models import *

class WFSUpdateTestCase(TestCase):
    multi_db = True
    fixtures = ['lds_update_test.json']

    def setUp(self):
        cursor = connections['lds_sample'].cursor()
        for table_name in ['sign_pnt', 'sign_pnt_update_2012_07_01']:
            cursor.execute("CREATE TABLE %s (id integer PRIMARY KEY, name text);" % table_name)
            cursor.execute("SELECT AddGeometryColumn('%s', 'wkb_geometry', 4326, 'POINT', 2);" % table_name)

        cursor.execute('ALTER TABLE sign_pnt_update_2012_07_01 ADD COLUMN "__change__" varchar(255);')

        feature_list = [
            (1, "Aardvarkville", 'ST_SetSRID(ST_MakePoint(168.0, -41.0), 4326)'),
            (2, "Beaverburg", 'ST_SetSRID(ST_MakePoint(169.0, -41.0), 4326)'),
            (3, "Cockatooton", 'ST_SetSRID(ST_MakePoint(170.0, -41.0), 4326)'),
            (4, "Deer City", 'ST_SetSRID(ST_MakePoint(168.0, -42.0), 4326)'),
            (5, "Elephantopolis", 'ST_SetSRID(ST_MakePoint(169.0, -42.0), 4326)'),
            (6, "Flamingodale", 'ST_SetSRID(ST_MakePoint(170.0, -42.0), 4326)'),
            ]

        for feature in feature_list:
            cursor.execute("INSERT INTO sign_pnt (id, name, wkb_geometry) VALUES (%s, '%s', %s);" % feature)

        update_list = [
            (2, "Greater Beaver Metro Area", 'ST_SetSRID(ST_MakePoint(169.0, -41.0), 4326)', 'UPDATE'),
            (3, "Cockatooton", 'ST_SetSRID(ST_MakePoint(170.0, -41.0), 4326)', 'DELETE'),
            (5, "Elephantopolis", 'ST_SetSRID(ST_MakePoint(169.0, -42.0), 4326)', 'UPDATE'),
            (6, "Flamingodale", 'ST_SetSRID(ST_MakePoint(170.0, -42.0), 4326)', 'DELETE'),
            (7, "Giraffeside", 'ST_SetSRID(ST_MakePoint(172.0, -44.0), 4326)', 'INSERT'),
            ]

        for update in update_list:
            cursor.execute("INSERT INTO sign_pnt_update_2012_07_01 (id, name, wkb_geometry, \"__change__\") VALUES (%s, '%s', %s, '%s');" % update)

    def tearDown(self):
        cursor = connections['lds_sample'].cursor()
        for table_name in ['sign_pnt', 'sign_pnt_update_2012_07_01']:
            cursor.execute("DROP TABLE %s;" % table_name)

    def test_base_data_loaded(self):
        c = connections['lds_sample'].cursor()
        c.execute("SELECT * FROM sign_pnt;")
        self.assertEqual(len(c.fetchall()), 6)

    def test_update_data_loaded(self):
        c = connections['lds_sample'].cursor()
        c.execute("SELECT * FROM sign_pnt_update_2012_07_01;")
        self.assertEqual(len(c.fetchall()), 5)

    def test_data_columns(self):
        c = connections['lds_sample'].cursor()

        data_columns, geom_column = osm.get_data_columns(c, "sign_pnt_update_2012_07_01")
        self.assertEqual(geom_column, "wkb_geometry")
        self.assertEqual(sorted(data_columns), [u"__change__", u"id", u"name"])

    def test_application_of_changeset(self):
        c = connections['lds_sample'].cursor()

        self.lds_sample = Dataset.objects.get(pk='lds_sample')
        self.root_user = User.objects.get(username='root')
        self.layer_in_dataset = self.lds_sample.layerindataset_set.all()[0]
        self.dataset_update = DatasetUpdate.objects.create(
            dataset=self.lds_sample,
            from_version="2012-01-01",
            to_version="2012-07-01",
            seq=1,
            owner=self.root_user)
        self.assertTrue(self.dataset_update.id)

        osm.apply_changeset_to_dataset(self.dataset_update, "sign_pnt_update_2012_07_01", self.layer_in_dataset)

        # Should have updated 2 and 5
        c.execute("SELECT name, ST_AsEWKT(wkb_geometry) FROM sign_pnt WHERE id = 2;");
        r = c.fetchone()
        self.assertEqual("Greater Beaver Metro Area", r[0])
        beaver_point = geos.GEOSGeometry(r[1])
        self.assertEqual(4326, beaver_point.srid)
        self.assertEqual(169, beaver_point.x)
        self.assertEqual(-41, beaver_point.y)
        c.execute("SELECT name FROM sign_pnt WHERE id = 5;");
        self.assertEqual("Elephantopolis", c.fetchone()[0])

        # Should have marked the UPDATE on 2 onto the WorksliceFeature
        wf = WorksliceFeature.objects.get(layer_in_dataset=self.layer_in_dataset, feature_id=2)
        self.assertEqual("updated", wf.get_dirty_display())

        # Should have deleted 3 and 6
        c.execute("SELECT count(*) FROM sign_pnt WHERE id IN (3, 6);")
        self.assertEqual(0, c.fetchone()[0])

        # Should have marked the DELETE on 3 onto the WorksliceFeature
        wf = WorksliceFeature.objects.get(layer_in_dataset=self.layer_in_dataset, feature_id=3)
        self.assertEqual("deleted", wf.get_dirty_display())

        # Should have inserted 7
        c.execute("SELECT name FROM sign_pnt WHERE id = 7;")
        self.assertEqual("Giraffeside", c.fetchone()[0])

        # Should have updated the version on the dataset
        # FIXME: this happens in DatasetUpdate#run, so can't be tested without testing that method
        #self.lds_sample = Dataset.objects.get(name=self.lds_sample.name)
        #self.assertEqual("2012-07-01", self.lds_sample.version)

        # Should have updated the feature count on the dataset
        self.layer_in_dataset = LayerInDataset.objects.get(pk=self.layer_in_dataset.id)
        self.assertEqual(5, self.layer_in_dataset.features_total)

        # Should have created a workslice to delete the deleted features

        # Should have marked the DatasetUpdate as complete
        # FIXME: this happends in DatasetUpdate#run, so can't be tested without testing that method
        #self.dataset_update = DatasetUpdate.objects.get(pk=self.dataset_update.id)
        #self.assertTrue(self.dataset_update.complete)


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
