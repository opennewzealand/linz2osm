from django.contrib import admin

from linz2osm.workslices.models import Workslice

# class WorksliceAdmin(admin.ModelAdmin):
#     pass

admin.site.register(Workslice)

