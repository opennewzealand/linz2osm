from django.contrib import admin

from linz2osm.workslices.models import Workslice


class WorksliceAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'checked_out_at', 'layer', 'user', 'dataset',)
    ordering = ('id',)
    readonly_fields = ('name', 'checked_out_at', 'status_changed_at', 'layer', 'dataset', 'bounds',)

admin.site.register(Workslice, WorksliceAdmin)
