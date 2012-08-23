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

import re

from django.contrib import admin
from django.template.loader import render_to_string

from linz2osm.data_dict.models import Layer, Tag, LayerInDataset, Dataset

class DatasetAdmin(admin.ModelAdmin):
    list_display = ('name', 'database_name', 'description', 'srid',)
    list_filter = ('srid',)
    ordering = ('name', 'database_name', 'description', 'srid',)
    readonly_fields = ('name', 'database_name', 'srid',)
    search_fields = ('name', 'database_name', 'description', 'srid',)

class LayerInDatasetInline(admin.StackedInline):
    model = LayerInDataset
    max_num = 1
    readonly_fields = ('dataset', 'layer', 'features_total', 'extent',)
    fields = ('tagging_approved', 'completed', 'dataset', 'layer', 'features_total',)
    exclude=('extent',)
    can_delete = False

class TagInline(admin.StackedInline):
    model = Tag
    extra = 2
    verbose_name = 'Tag'
    verbose_name_plural = 'Tags'

# TODO: filter by geometry type
# TODO: custom templates so choices aren't so ugly
class TaggingApprovedListFilter(admin.SimpleListFilter):
    title = 'tagging approved'
    parameter_name = 'tagging_approved'

    def lookups(self, request, model_admin):
        datasets = Dataset.objects.order_by('description').all()
        return tuple(
            [("yes_%s" % ds.name, "%s approved" % (ds.description,)) for ds in datasets] +
            [("no_%s" % ds.name, "%s not approved" % (ds.description),) for ds in datasets] +
            [('none', 'None approved'),
             ('any', 'Any approved'),
             ('all', 'All approved'),
             ('notall', 'Not all approved'),
             ('nodatasets', 'Not available in any datasets'),
             ])

    def queryset(self, request, queryset):
        if self.value() == 'nodatasets':
            return queryset.exclude(layerindataset__id__isnull=False)
        elif self.value() == 'all':
            return queryset.exclude(layerindataset__tagging_approved=False).filter(layerindataset__tagging_approved=True)
        elif self.value() == 'none':
            return queryset.exclude(layerindataset__tagging_approved=True).filter(layerindataset__tagging_approved=False)
        elif self.value() == 'any':
            return queryset.filter(layerindataset__tagging_approved=True)
        elif self.value() == 'notall':
            return queryset.filter(layerindataset__tagging_approved=False)
        else:
            matches = re.match('(?P<condition>yes|no)_(?P<dataset_name>\w+)', str(self.value()))
            if matches:
                condition = matches.group('condition')
                dataset_name = matches.group('dataset_name')
                if condition == 'yes':
                    return queryset.filter(layerindataset__dataset_id=dataset_name, layerindataset__tagging_approved=True)
                elif condition == 'no':
                    return queryset.filter(layerindataset__dataset_id=dataset_name, layerindataset__tagging_approved=False)

        return queryset
    
class CompletedListFilter(admin.SimpleListFilter):
    title = 'completed'
    parameter_name = 'completed'

    def lookups(self, request, model_admin):
        datasets = Dataset.objects.order_by('description').all()
        return tuple(
            [("yes_%s" % ds.name, "%s completed" % (ds.description,)) for ds in datasets] +
            [("no_%s" % ds.name, "%s not completed" % (ds.description),) for ds in datasets] +
            [('none', 'None completed'),
             ('any', 'Any completed'),
             ('all', 'All completed'),
             ('notall', 'Not all completed'),
             ('nodatasets', 'Not available in any datasets'),
             ])

    def queryset(self, request, queryset):
        if self.value() == 'nodatasets':
            return queryset.exclude(layerindataset__id__isnull=False)
        elif self.value() == 'all':
            return queryset.exclude(layerindataset__completed=False).filter(layerindataset__completed=True)
        elif self.value() == 'none':
            return queryset.exclude(layerindataset__completed=True).filter(layerindataset__completed=False)
        elif self.value() == 'any':
            return queryset.filter(layerindataset__completed=True)
        elif self.value() == 'notall':
            return queryset.filter(layerindataset__completed=False)
        else:
            matches = re.match('(?P<condition>yes|no)_(?P<dataset_name>\w+)', str(self.value()))
            if matches:
                condition = matches.group('condition')
                dataset_name = matches.group('dataset_name')
                if condition == 'yes':
                    return queryset.filter(layerindataset__dataset_id=dataset_name, layerindataset__completed=True)
                elif condition == 'no':
                    return queryset.filter(layerindataset__dataset_id=dataset_name, layerindataset__completed=False)

        return queryset
    
class LayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'entity', 'geometry_type', 'stats_link', 'tag_count', 'dataset_descriptions', 'notes',)
    list_filter = (TaggingApprovedListFilter, CompletedListFilter, 'geometry_type', 'datasets', 'entity',)
    inlines = [
        LayerInDatasetInline,
        TagInline,
    ]
    ordering = ('name',)
    readonly_fields = ('name', 'entity', 'geometry_type')
    search_fields = ('name', 'notes',)

    class Media:
        css = {
            'all': ('code_exec.css',),
        }
        js = ("jquery.cookie.js", "code_exec.js",)
            
    def tag_count(self, obj):
        return obj.tags.count()
    tag_count.short_description = 'Defined Tags'
    
    def dataset_descriptions(self, obj):
        return render_to_string('admin/data_dict/layer/dataset_descriptions.html', {
                'layer_in_datasets': obj.layerindataset_set.all()
                })
    dataset_descriptions.short_description = 'Available in which datasets'
    dataset_descriptions.allow_tags = True

    def stats_link(self, obj):
        return "<a href='/data_dict/layer/%s/stats/'>Layer Stats</a>" % obj.name
    stats_link.short_description = 'Statistics'
    stats_link.allow_tags = True

class TagAdmin(admin.ModelAdmin):
    list_display = ('tag',)
    ordering = ('tag',)
    exclude = ('layer',)
    
    class Media:
        css = {
            'all': ('code_exec.css',),
        }
        js = ("jquery.cookie.js", "code_exec.js",)
            
    def queryset(self, request):
        # only tags without layers (default tags)
        return self.model.objects.default()

    
admin.site.register(Layer, LayerAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Dataset, DatasetAdmin)
