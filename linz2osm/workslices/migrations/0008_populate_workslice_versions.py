# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Don't use "from appname.models import ModelName".
        # Use orm.ModelName to refer to models in this application,
        # and orm['appname.ModelName'] for models in other applications.
        for lid in orm['data_dict.LayerInDataset'].objects.all():
            lid.workslice_set.update(version=lid.dataset.version)

    def backwards(self, orm):
        orm.Workslice.objects.update(version=None)

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'data_dict.dataset': {
            'Meta': {'object_name': 'Dataset'},
            'database_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'generating_deletions_osm': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_dict.Group']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'primary_key': 'True'}),
            'srid': ('django.db.models.fields.IntegerField', [], {}),
            'update_method': ('django.db.models.fields.CharField', [], {'default': "'manual'", 'max_length': '255'}),
            'version': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'data_dict.group': {
            'Meta': {'object_name': 'Group'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'primary_key': 'True'})
        },
        u'data_dict.layer': {
            'Meta': {'object_name': 'Layer'},
            'datasets': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['data_dict.Dataset']", 'through': u"orm['data_dict.LayerInDataset']", 'symmetrical': 'False'}),
            'entity': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '200', 'blank': 'True'}),
            'geometry_type': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_dict.Group']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pkey_name': ('django.db.models.fields.CharField', [], {'default': "'ogc_fid'", 'max_length': '255'}),
            'processors': ('linz2osm.utils.db_fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'special_dataset_name_tag': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'special_dataset_version_tag': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'special_end_node_field_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'special_node_reuse_logic': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'special_node_tag_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'special_start_node_field_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'tags_ql': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'wfs_cql_filter': ('django.db.models.fields.TextField', [], {'max_length': '255', 'blank': 'True'}),
            'wfs_type_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'data_dict.layerindataset': {
            'Meta': {'object_name': 'LayerInDataset'},
            'completed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'dataset': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_dict.Dataset']"}),
            'extent': ('django.contrib.gis.db.models.fields.GeometryField', [], {'null': 'True'}),
            'features_total': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_deletions_dump_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_dict.Layer']"}),
            'tagging_approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'workslices.workslice': {
            'Meta': {'object_name': 'Workslice'},
            'checked_out_at': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'checkout_extent': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'feature_count': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'followup_deadline': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'layer_in_dataset': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_dict.LayerInDataset']"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'status_changed_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'version': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'workslices.workslicefeature': {
            'Meta': {'object_name': 'WorksliceFeature'},
            'dirty': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'feature_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'layer_in_dataset': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_dict.LayerInDataset']"}),
            'workslice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['workslices.Workslice']"})
        }
    }

    complete_apps = ['workslices']
    symmetrical = True
