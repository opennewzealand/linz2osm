from django.contrib.gis.db import models
from django.contrib.gis.measure import D
from django.contrib.gis import geos
from django.db import transaction

class Boundary(models.Model):
    LEVELS = [
        (3, "Area Unit"),
        (2, "Urban Area"),
        (1, "City/District"),
        (0, "Region"),
    ]
    
    level = models.IntegerField(db_index=True, choices=LEVELS);
    name = models.CharField(max_length=255)
    poly = models.GeometryField('Boundary', srid=4326, null=True)
    
    poly_display = models.MultiPolygonField('Boundary', srid=900913, null=True)
    parent = models.ForeignKey('self', related_name='children', null=True)
    neighbours = models.ManyToManyField('self', related_name='neighbours', null=True)
    
    objects = models.GeoManager()
    
    class Meta:
        ordering = ('level', 'name',)
        verbose_name_plural = 'Boundaries'
    
    def __unicode__(self):
        return '%s (%s)' % (self.name, self.get_level_display())
    
    def update_poly_display(self):
        self.poly_display = None
        if self.poly:
            pd = self.poly.simplify(0.0032).transform(900913, True)
            
            if isinstance(pd, geos.Polygon):
                pd = geos.MultiPolygon(pd)
            
            if isinstance(pd, geos.MultiPolygon):
                self.poly_display = pd
        
        self.save()
    
    @transaction.commit_on_success
    def update_children(self):
        for o in Boundary.objects.only('id').filter(level=self.level+1, poly__within=self.poly):
            o.parent = self
            o.save()
    
    @transaction.commit_on_success
    def update_neighbours(self):
        qs = Boundary.objects.only('id').filter(level=self.level)
        qs = qs.filter(poly__bboverlaps=self.poly.envelope.buffer(0.0032), poly__dwithin=(self.poly, 0.00064))
        self.neighbours = qs
        self.save()
    
    @property
    def extent(self):
        return self.poly.extent

