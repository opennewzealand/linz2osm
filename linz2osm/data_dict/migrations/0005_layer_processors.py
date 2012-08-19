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
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):
    
    def _get_geom_type(self, name):
        end = name.rsplit('_', 1)[-1]
        if end in ('pnt', 'name', 'text', 'feat'):
            return 'POINT'
        elif end in ('cl', 'edge', 'edg', 'coastline', 'contour'):
            return 'LINESTRING'
        elif end in ('poly',):
            return 'POLYGON'
        else:
            return None
    
    def forwards(self, orm):
        "Populate processors from wind_polygons_ccw/reverse_line_coords."
        for layer in orm.Layer.objects.all():
            p = []
            geom_type = self._get_geom_type(layer.name)
            
            if geom_type in ('POLYGON', 'MULTIPOLYGON'):
                if layer.wind_polygons_ccw:
                    p.append(('PolyWindingCCW', {}))
                else:
                    p.append(('PolyWindingCW', {}))
            elif geom_type in ('LINESTRING', 'MULTILINESTRING'):
                if layer.reverse_line_coords:
                    p.append(('ReverseLine', {}))
            
            if p:
                layer.processors = p
                layer.save()
    
    def backwards(self, orm):
        "Populate wind_polygons_ccw/reverse_line_coords from processors."
        for layer in orm.Layer.objects.all():
            for pk in layer.processors.keys():
                if pk == 'PolyWindingCW':
                    layer.wind_polygons_ccw = False
                    layer.save()
                elif pk == 'ReverseLine':
                    layer.reverse_line_coords = True
                    layer.save()
    
    models = {
        'data_dict.layer': {
            'Meta': {'object_name': 'Layer'},
            'entity': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '200', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'processors': ('linz2osm.utils.db_fields.JSONField', [], {'null': 'True'}),
            'reverse_line_coords': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
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
