#  LINZ-2-OSM
#  Copyright (C) Koordinates Ltd.
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
from django import forms
import pydermonkey

from linz2osm.data_dict.models import Layer, Tag, LayerInDataset, Dataset, Group, Member

class LayerInDatasetInline(admin.StackedInline):
    model = LayerInDataset
    max_num = 1
    readonly_fields = ('dataset', 'layer', 'features_total', 'extent',)
    fields = ('tagging_approved', 'completed', 'dataset', 'layer', 'features_total',)
    exclude=('extent',)
    can_delete = False

class DatasetAdmin(admin.ModelAdmin):
    inlines = [
        LayerInDatasetInline,
    ]
    list_display = ('name', 'database_name', 'description', 'version', 'srid', 'group')
    list_filter = ('srid', 'group', 'version',)
    ordering = ('name', 'database_name', 'description', 'version', 'srid', 'group')
    readonly_fields = ('name', 'database_name', 'srid', 'update_link')
    search_fields = ('name', 'database_name', 'description', 'version', 'srid', 'group')
    save_on_top = True

    def update_link(self, obj):
        if obj.update_method == "manual":
            return "Manual updates only"
        else:
            return "<a href='/data_dict/dataset/%s/update'>Update with %s</a>, <a href='/data_dict/dataset/%s/merge_deletions'>Purge deleted data from OSM</a>" % (obj.name, obj.get_update_method_display(), obj.name)
    update_link.short_description = 'Update'
    update_link.allow_tags = True

    # http://stackoverflow.com/questions/4343535/django-admin-make-a-field-read-only-when-modifying-obj-but-required-when-adding
    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('version',)
        return self.readonly_fields


class TagInlineForm(forms.ModelForm):
    class Meta:
        model = Tag

    # def __init__(self, *args, **kwargs):
    #     super(TagInlineForm, self).__init__(*args, **kwargs)

    def clean_code(self):
        code_text = self.cleaned_data['code']

        js = pydermonkey.Runtime().new_context()
        try:
            js.compile_script(code_text, '<Tag Code>', 1)
        except (Exception,), e:
            e_msg = js.get_property(e.args[0], 'message')
            e_lineno = js.get_property(e.args[0], 'lineNumber')

            raise forms.ValidationError("Error: %s (line %d)" % (e_msg, e_lineno))
        return code_text

class TagInline(admin.StackedInline):
    model = Tag
    extra = 2
    verbose_name = 'Tag'
    verbose_name_plural = 'Tags'
    form = TagInlineForm

class MemberInlineForm(forms.ModelForm):
    class Meta:
        model = Member

class LayerMemberInline(admin.StackedInline):
    model = Member
    fk_name = 'member_layer'
    extra = 1
    verbose_name = 'Member'
    verbose_name_plural = 'Members'
    form = MemberInlineForm

class GroupTagInline(TagInline):
    exclude = ("layer",)

class LayerTagInline(TagInline):
    exclude = ("group",)

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
    list_display = ('name', 'entity', 'geometry_type', 'group', 'stats_link', 'tag_count', 'dataset_descriptions', 'notes',)
    list_filter = (TaggingApprovedListFilter, CompletedListFilter, 'geometry_type', 'group', 'datasets', 'entity',)
    inlines = [
        LayerInDatasetInline,
        LayerTagInline,
        LayerMemberInline
    ]
    ordering = ('name', 'group',)
    readonly_fields = ('special_node_reuse_logic',)
    search_fields = ('name', 'notes',)
    save_on_top = True

    # http://stackoverflow.com/questions/4343535/django-admin-make-a-field-read-only-when-modifying-obj-but-required-when-adding
    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('name', 'entity', 'geometry_type', 'pkey_name', 'wfs_type_name', 'wfs_cql_filter')
        return self.readonly_fields

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
    list_display = ('tag', 'apply_to')
    ordering = ('tag',)
    exclude = ('layer',)
    save_on_top = True

    class Media:
        css = {
            'all': ('code_exec.css',),
        }
        js = ("jquery.cookie.js", "code_exec.js",)

    def queryset(self, request):
        # only tags without layers (default tags)
        return self.model.objects.default()

class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    ordering = ('name', 'description')
    inlines = [
        GroupTagInline,
    ]
    save_on_top = True

admin.site.register(Group, GroupAdmin)
admin.site.register(Layer, LayerAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Dataset, DatasetAdmin)
