# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Group'
        db.create_table('data_dict_group', (
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255, primary_key=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('data_dict', ['Group'])

        # Adding field 'Dataset.group'
        db.add_column('data_dict_dataset', 'group',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_dict.Group'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Tag.dataset'
        db.add_column('data_dict_tag', 'dataset',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_dict.Dataset'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Tag.group'
        db.add_column('data_dict_tag', 'group',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_dict.Group'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Layer.group'
        db.add_column('data_dict_layer', 'group',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_dict.Group'], null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'Group'
        db.delete_table('data_dict_group')

        # Deleting field 'Dataset.group'
        db.delete_column('data_dict_dataset', 'group_id')

        # Deleting field 'Tag.dataset'
        db.delete_column('data_dict_tag', 'dataset_id')

        # Deleting field 'Tag.group'
        db.delete_column('data_dict_tag', 'group_id')

        # Deleting field 'Layer.group'
        db.delete_column('data_dict_layer', 'group_id')


    models = {
        'data_dict.dataset': {
            'Meta': {'object_name': 'Dataset'},
            'database_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['data_dict.Group']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'primary_key': 'True'}),
            'srid': ('django.db.models.fields.IntegerField', [], {})
        },
        'data_dict.group': {
            'Meta': {'object_name': 'Group'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'primary_key': 'True'})
        },
        'data_dict.layer': {
            'Meta': {'object_name': 'Layer'},
            'datasets': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['data_dict.Dataset']", 'through': "orm['data_dict.LayerInDataset']", 'symmetrical': 'False'}),
            'entity': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '200', 'blank': 'True'}),
            'geometry_type': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['data_dict.Group']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'processors': ('linz2osm.utils.db_fields.JSONField', [], {'null': 'True', 'blank': 'True'})
        },
        'data_dict.layerindataset': {
            'Meta': {'object_name': 'LayerInDataset'},
            'completed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'dataset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['data_dict.Dataset']"}),
            'extent': ('django.contrib.gis.db.models.fields.GeometryField', [], {'null': 'True'}),
            'features_total': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['data_dict.Layer']"}),
            'tagging_approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'data_dict.tag': {
            'Meta': {'unique_together': "(('layer', 'tag'),)", 'object_name': 'Tag'},
            'code': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'dataset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['data_dict.Dataset']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['data_dict.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'tags'", 'null': 'True', 'to': "orm['data_dict.Layer']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['data_dict']