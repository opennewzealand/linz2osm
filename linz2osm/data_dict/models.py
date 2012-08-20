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

import decimal

import pydermonkey
from django.db import models, connections
from django.db.models import Sum
from django.utils import text
from django.conf import settings
from django.contrib.gis.db import models as geomodels

from linz2osm.utils.db_fields import JSONField
from linz2osm.convert import processing, osm

processor_list_html = '<ul class="help">' + ''.join(['<li><strong>%s</strong>: %s</li>' % p for p in sorted(processing.get_available().items())]) + '</ul>'

class DatasetManager(models.Manager):
    def clear_datasets(self):
        # cascades and also drops LayerInDatasets
        Dataset.objects.all().delete()
    
    def generate_datasets(self):
        for name, details in settings.DATABASES.items():
            if name != 'default':
                if Dataset.objects.filter(name=name).exists():
                    dataset = Dataset.objects.get(name=name)
                else:
                    dataset = self.create(name = name,
                                          database_name = details['NAME'],
                                          description = details['_description'],
                                          srid = int(details['_srid']))
                    
                for layer in Layer.objects.all():
                    if dataset.has_layer_in_schema(layer.name):
                        LayerInDataset.objects.create_layer_in_dataset(layer, dataset)


class Dataset(models.Model):
    name = models.CharField(max_length=255, unique=True, primary_key=True)
    database_name = models.CharField(max_length=255)
    description = models.TextField()
    srid = models.IntegerField()

    def has_layer_in_schema(self, layer_name):
        cursor = connections[self.name].cursor()
        cursor.execute("SELECT true FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename=%s;", [layer_name])
        return (cursor.fetchone() is not None)
    
    def __unicode__(self):
        return unicode(self.description)

    @models.permalink
    def get_absolute_url(self):
        return ('linz2osm.data_dict.views.show_dataset', (), {'dataset_id': self.name})
    
    objects = DatasetManager()
    
class Layer(models.Model):
    GEOTYPE_CHOICES = [
        ('POINT', 'Point'),
        ('LINESTRING', 'Linestring'),
        ('POLYGON', 'Polygon'),
        ]
    
    name = models.CharField(max_length=100, primary_key=True)
    entity = models.CharField(max_length=200, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    processors = JSONField(blank=True, null=True, help_text=('What geometry processors to apply. In the format [ ["name",{"arg":"value", ...}], ...]. Available processors:<br/>' + processor_list_html))
    datasets = models.ManyToManyField(Dataset, through='LayerInDataset')
    geometry_type = models.CharField(max_length=255, blank=True, choices=GEOTYPE_CHOICES)
    
    def __unicode__(self):
        return unicode(self.name)

    def deduce_geometry_type(self):
        end = self.name.rsplit('_', 1)[-1]
        if end in ('pnt', 'pnt2', 'name', 'text', 'feat'):
            return 'POINT'
        elif end in ('cl', 'edge', 'edg', 'coastline', 'contour'):
            return 'LINESTRING'
        elif end in ('poly',):
            return 'POLYGON'
        else:
            # unknown
            return None
        
    @property
    def linz_dictionary_url(self):
        BASE_URL = "http://apps.linz.govt.nz/topo-data-dictionary/index.aspx?page=class-%s"
        return BASE_URL % self.name
    
    def get_all_tags(self):
        # if we override a default one, use the specific one
        tags = dict([(t.tag, t) for t in Tag.objects.default()])
        for t in self.tags.all():
            tags[t.tag] = t
        return tags.values()
    
    def get_statistics(self, dataset_id=None):
        from linz2osm.convert.osm import get_layer_stats
        if dataset_id:
            return get_layer_stats(dataset_id, self)
        else:
            r = {}
            for ds in self.datasets.all():
                r[(ds.name, ds.description)] = get_layer_stats(ds.name, self)
            return r
    
    def get_processors(self):
        from linz2osm.convert.processing import get_class
        p_list = []
        if self.processors:
            for p_id,p_opts in self.processors:
                p_cls = get_class(p_id)
                p = p_cls(**p_opts)
                p_list.append(p)
        return p_list


class LayerInDatasetManager(geomodels.GeoManager):
    def create_layer_in_dataset(self, layer, dataset):
        if not LayerInDataset.objects.filter(layer=layer, dataset=dataset).exists():
            # TODO: merge with osm.get_layer_feature_count

            stats = osm.get_layer_stats(dataset.name, layer)
            
            cursor = connections[dataset.name].cursor()
            cursor.execute('SELECT count(1) FROM %s;' % layer.name)
            feature_ct = cursor.fetchone()[0]
            
            return self.create(layer=layer,
                               dataset=dataset,
                               features_total=stats['feature_count'],
                               extent=stats['extent']
                               )
        
class LayerInDataset(geomodels.Model):
    objects = LayerInDatasetManager()

    dataset = geomodels.ForeignKey(Dataset)
    layer = geomodels.ForeignKey(Layer)
    features_total = geomodels.IntegerField()
    extent = geomodels.GeometryField(null=True)
    tagging_approved = geomodels.BooleanField(default=False)
    completed = geomodels.BooleanField(default=False)
    
    def __unicode__(self):
        return "%s / %s" % (self.dataset.description, self.layer.name,)

    @models.permalink
    def get_absolute_url(self):
        return ('linz2osm.workslices.views.create_workslice', (), {'layer_in_dataset_id': self.id})

    def get_statistics_for(self, field_name):
        return osm.get_field_stats(self.dataset.name, self.layer, field_name)
    
    def js_display_bounds_array(self):
        min_x, min_y, max_x, max_y = [f for f in self.extent.extent]
        x_margin = (max_x - min_x) * 0.1 
        y_margin = (max_y - min_y) * 0.1 
        return unicode([min_x - x_margin, min_y - y_margin, max_x + x_margin, max_y + y_margin])

    def js_extent_geojson(self):
        return """ {
            "geometry": %s,
            "type": "Feature",
            "properties": {
                "model": "LayerInDataset"
            }
        } """ % self.extent.geojson

    def js_workslice_geojson(self):
        shown_workslices = self.workslice_set.filter(state__in=('processing','out','complete','blocked',))
        
        return """
            { "type": "FeatureCollection",
              "features": [%s],
              "crs": {
                  "type" : "name",
                  "properties" : {
                      "name" : "EPSG:4326"
                  }
              }
            }
        """ % ",".join([self.js_extent_geojson(), ",".join(ws.js_feature_geojson() for ws in shown_workslices)])

    def features_complete(self):
        return self.workslice_set.filter(state__in=('complete',)).aggregate(Sum('feature_count'))['feature_count__sum'] or 0

    def features_complete_pct(self):
        return (100.0 * self.features_complete() / self.features_total)
    
    def features_in_progress(self):
        return self.workslice_set.filter(state__in=('processing','out','blocked',)).aggregate(Sum('feature_count'))['feature_count__sum'] or 0

    def features_in_progress_pct(self):
        return (100.0 * self.features_in_progress() / self.features_total)
    
    def features_todo(self):
        return (self.features_total - self.features_complete() - self.features_in_progress()) or 0
    
    def features_todo_pct(self):
        return (100.0 * self.features_todo() / self.features_total)

                           
class TagManager(models.Manager):
    def eval(self, code, fields):
        eval_fields = {}
        for fk,fv in fields.items():
            if isinstance(fv, decimal.Decimal):
                fv = float(fv)
            eval_fields[fk] = fv
        
        js = pydermonkey.Runtime().new_context()
        try:
            script = js.compile_script(code, '<Tag Code>', 1)

            context = js.new_object()
            js.init_standard_classes(context)
            
            js.define_property(context, 'value', None);
            context_fields = js.new_object()
            for fk,fv in eval_fields.items():
                js.define_property(context_fields, fk, fv)
            js.define_property(context, 'fields', context_fields) 
            
            js.execute_script(context, script)
            
            value = js.get_property(context, 'value')
            if value is pydermonkey.undefined:
                value = None
            return value
        except pydermonkey.error, e:
            e_msg = js.get_property(e.args[0], 'message')
            e_lineno = js.get_property(e.args[0], 'lineNumber')
            en = Tag.ScriptError("%s (line %d)" % (e_msg, e_lineno))
            en.data = eval_fields
            raise en

    def default(self):
        return self.get_query_set().filter(layer__isnull=True)

class Tag(models.Model):
    objects = TagManager()
    
    layer = models.ForeignKey(Layer, null=True, related_name='tags')
    tag = models.CharField(max_length=100, help_text="OSM tag name")
    code = models.TextField(blank=True, help_text="Javascript code that sets the 'value' paramter to a non-null value to set the tag. 'fields' is an object with all available attributes for the current record")
    
    
    class Meta:
        unique_together = ('layer', 'tag',)
        verbose_name = 'Default Tag'
        verbose_name_plural = 'Default Tags'
    
    class ScriptError(Exception):
        data = None
    
    def __unicode__(self):
        return self.tag
    
    def eval(self, fields):
        return Tag.objects.eval(self.code, fields)
        
