# -*- coding: utf-8 -*-
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

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'WorksliceFeature'
        db.create_table('workslices_workslicefeature', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('workslice', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['workslices.Workslice'])),
            ('feature_id', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('workslices', ['WorksliceFeature'])


        # Changing field 'Workslice.checkout_extent'
        db.alter_column('workslices_workslice', 'checkout_extent', self.gf('django.contrib.gis.db.models.fields.MultiPolygonField')())

    def backwards(self, orm):
        # Deleting model 'WorksliceFeature'
        db.delete_table('workslices_workslicefeature')


        # Changing field 'Workslice.checkout_extent'
        db.alter_column('workslices_workslice', 'checkout_extent', self.gf('django.contrib.gis.db.models.fields.PolygonField')())

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'data_dict.dataset': {
            'Meta': {'object_name': 'Dataset'},
            'database_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'primary_key': 'True'}),
            'srid': ('django.db.models.fields.IntegerField', [], {})
        },
        'data_dict.layer': {
            'Meta': {'object_name': 'Layer'},
            'datasets': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['data_dict.Dataset']", 'through': "orm['data_dict.LayerInDataset']", 'symmetrical': 'False'}),
            'entity': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '200', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'processors': ('linz2osm.utils.db_fields.JSONField', [], {'null': 'True', 'blank': 'True'})
        },
        'data_dict.layerindataset': {
            'Meta': {'object_name': 'LayerInDataset'},
            'dataset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['data_dict.Dataset']"}),
            'extent': ('django.contrib.gis.db.models.fields.GeometryField', [], {'null': 'True'}),
            'features_total': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['data_dict.Layer']"})
        },
        'workslices.workslice': {
            'Meta': {'object_name': 'Workslice'},
            'checked_out_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'checkout_extent': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'feature_count': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'followup_deadline': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'layer_in_dataset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['data_dict.LayerInDataset']"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'status_changed_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'workslices.workslicefeature': {
            'Meta': {'object_name': 'WorksliceFeature'},
            'feature_id': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'workslice': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['workslices.Workslice']"})
        }
    }

    complete_apps = ['workslices']
