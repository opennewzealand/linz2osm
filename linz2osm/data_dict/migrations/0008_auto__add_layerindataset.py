# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LayerInDataset'
        db.create_table('data_dict_layerindataset', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('dataset', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_dict.Dataset'])),
            ('layer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_dict.Layer'])),
            ('features_total', self.gf('django.db.models.fields.IntegerField')()),
            ('extent', self.gf('django.contrib.gis.db.models.fields.GeometryField')(null=True)),
        ))
        db.send_create_signal('data_dict', ['LayerInDataset'])


    def backwards(self, orm):
        # Deleting model 'LayerInDataset'
        db.delete_table('data_dict_layerindataset')


    models = {
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
        'data_dict.tag': {
            'Meta': {'unique_together': "(('layer', 'tag'),)", 'object_name': 'Tag'},
            'code': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tags'", 'null': 'True', 'to': "orm['data_dict.Layer']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['data_dict']