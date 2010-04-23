from django.contrib.gis.db import models

class Boundary(models.Model):
    LEVELS = [
        (3, "Area Unit"),
        (2, "Urban Area"),
        (1, "City/District"),
        (0, "Region"),
    ]
    
    level = models.IntegerField(db_index=True, choices=LEVELS);
    name = models.CharField(max_length=255)
    poly = models.GeometryField(srid=4326, null=True)
    poly_display = models.GeometryField(srid=900913, null=True)
    
    objects = models.GeoManager()
    
    class Meta:
        ordering = ('level', 'name',)
        verbose_name_plural = 'Boundaries'
    
    def __unicode__(self):
        return '%s (%s)' % (self.name, self.get_level_display())
    
    def save(self, *args, **kwargs):
        if self.poly:
            self.poly_display = self.poly.transform(900913)
        else:
            self.poly_display = None
        super(Boundary, self).save(*args, **kwargs)
    
    def get_parent(self):
        """ get the parent boundary, or None """
        parent_level = self.level - 1
        if parent_level < 0:
            return None
        
        objs = Boundary.objects.filter(level=parent_level, poly__contains=self.poly.centroid)[:1]
        if len(objs):
            return objs[0]
        else:
            return None
        
    @property
    def extent(self):
        return self.poly.extent

