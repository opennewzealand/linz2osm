# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding field 'Layer.wind_polygons_ccw'
        db.add_column('data_dict_layer', 'wind_polygons_ccw', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True), keep_default=False)
    
    
    def backwards(self, orm):
        
        # Deleting field 'Layer.wind_polygons_ccw'
        db.delete_column('data_dict_layer', 'wind_polygons_ccw')
    
    
    models = {
        'data_dict.layer': {
            'Meta': {'object_name': 'Layer'},
            'entity': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '200', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'wind_polygons_ccw': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
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
