# encoding: utf-8
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
        
        # Adding model 'Layer'
        db.create_table('data_dict_layer', (
            ('notes', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, primary_key=True)),
            ('entity', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=200, blank=True)),
        ))
        db.send_create_signal('data_dict', ['Layer'])

        # Adding model 'Tag'
        db.create_table('data_dict_tag', (
            ('code', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('layer', self.gf('django.db.models.fields.related.ForeignKey')(related_name='tags', null=True, to=orm['data_dict.Layer'])),
            ('tag', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('data_dict', ['Tag'])

        # Adding unique constraint on 'Tag', fields ['layer', 'tag']
        db.create_unique('data_dict_tag', ['layer_id', 'tag'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'Layer'
        db.delete_table('data_dict_layer')

        # Deleting model 'Tag'
        db.delete_table('data_dict_tag')

        # Removing unique constraint on 'Tag', fields ['layer', 'tag']
        db.delete_unique('data_dict_tag', ['layer_id', 'tag'])
    
    
    models = {
        'data_dict.layer': {
            'Meta': {'object_name': 'Layer'},
            'entity': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '200', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'})
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
