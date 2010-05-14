from django.contrib.gis import admin

from linz2osm.boundaries.models import Boundary

class BoundaryAdmin(admin.OSMGeoAdmin):
    exclude = ('poly',)
    modifiable = False
    search_fields = ('name',)
    list_filter = ('level',)
    fieldsets = (
        (None, {
            'fields': ('name', 'level', 'poly_display', ),
        }),
        ('Relations', {
            'fields': ('parent', 'neighbours',),
        }),
    )
    readonly_fields = ('level', 'name', 'parent', 'neighbours',)
    list_display = ('name', 'level',)

    def parent(self, obj):
        p = obj.parent
        if p:
            return '<a href="%s">%s</a>' % (p.get_absolute_url(), str(p))
        else:
            return '(None)'
    parent.short_description = 'Parent Area'
    
    def neighbours(self, obj):
        neighbours = obj.neighbours.only('name')
        if neighbours:
            return ', '.join(['<a href="%s">%s</a>' % (n.get_absolute_url(), n.name) for n in neighbours])
        else:
            return '(None)'
    neighbours.short_description = 'Neighbouring Areas'

admin.site.register(Boundary, BoundaryAdmin)
