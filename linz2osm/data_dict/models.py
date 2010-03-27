import traceback

from django.db import models
from django.utils import text
from django.core.exceptions import ValidationError

class Layer(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    entity = models.CharField(max_length=200, blank=True, db_index=True)
    
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

class TagManager(models.Manager):
    def eval(self, code, fields):
        c_in = {
            'fields': fields,
        }
        c_out = {}
        exec code in c_in, c_out
        return c_out.get('value')

class Tag(models.Model):
    objects = TagManager()
    
    layer = models.ForeignKey(Layer, null=True, related_name='tags')
    tag = models.CharField(max_length=100)
    code = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('layer', 'tag',)
        verbose_name = 'Default Tag'
        verbose_name_plural = 'Default Tags'
    
    def __unicode__(self):
        return self.tag
    
    def clean(self):
        # Don't allow code that doesn't compile.
        self.code = self.code.replace('\r\n', '\n')
        try:
            compile(self.code, '<tag code>', 'exec')
        except SyntaxError, e:
            raise ValidationError('Error compiling code:' + str(e))

    def eval(self, fields):
        return Tag.objects.eval(self.code, fields)
        
    