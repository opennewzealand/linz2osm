from django.contrib import admin

from linz2osm.data_dict.models import Layer, Tag

class TagInline(admin.StackedInline):
    model = Tag
    extra = 3
    verbose_name = 'Tag'
    verbose_name_plural = 'Tags'

class LayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'entity', 'get_geometry_type_display', 'tag_count', 'notes',)
    list_filter = ('entity',)
    inlines = [
        TagInline,
    ]
    ordering = ('name',)
    readonly_fields = ('name', 'entity',)

    class Media:
        css = {
            'all': ('code_exec.css',),
        }
        js = ("jquery.cookie.js", "code_exec.js",)
            
    def tag_count(self, obj):
        return obj.tags.count()
    tag_count.short_description = 'Defined Tags'

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
        return self.model._default_manager.get_query_set().filter(layer__isnull=True)

admin.site.register(Layer, LayerAdmin)
admin.site.register(Tag, TagAdmin)

