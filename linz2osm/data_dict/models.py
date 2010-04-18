import decimal

import pydermonkey
from django.db import models
from django.utils import text

class Layer(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    entity = models.CharField(max_length=200, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    
    def __unicode__(self):
        return unicode(self.name)
    
    @property
    def geometry_type(self):
        end = self.name.rsplit('_', 1)[-1]
        if end in ('pnt', 'name', 'text', 'feat'):
            return 'POINT'
        elif end in ('cl', 'edge', 'edg', 'coastline', 'contour'):
            return 'LINESTRING'
        elif end in ('poly',):
            return 'POLYGON'
        else:
            # unknown
            return None
    
    def get_geometry_type_display(self):
        gt = self.geometry_type
        if gt is None:
            gt = "Unknown"
        return text.capfirst(gt.lower())
    get_geometry_type_display.short_description = 'Geometry Type'
    
    @property
    def linz_dictionary_url(self):
        BASE_URL = "http://www.linz.govt.nz/topography/technical-specs/data-dictionary/index.aspx?page=class-%s"
        return BASE_URL % self.name
    
    def get_all_tags(self):
        # if we override a default one, use the specific one
        tags = dict([(t.tag, t) for t in Tag.objects.default()])
        for t in self.tags.all():
            tags[t.tag] = t
        return tags.values()
    
    def get_datasets(self):
        from linz2osm.convert.osm import get_layer_datasets
        return get_layer_datasets(self)

    def get_statistics(self, dataset_id=None):
        from linz2osm.convert.osm import get_layer_stats
        if dataset_id:
            return get_layer_stats(dataset_id, self)
        else:
            r = {}
            for ds in self.get_datasets():
                r[ds] = get_layer_stats(ds[0], self)
            return r

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
        
