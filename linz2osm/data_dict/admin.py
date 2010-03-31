from django.contrib import admin

from linz2osm.data_dict.models import Layer, Tag

class TagInline(admin.StackedInline):
    model = Tag
    extra = 3
    verbose_name = 'Tag'
    verbose_name_plural = 'Tags'

class LayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'entity', 'get_geometry_type_display', 'tag_count', 'datasets', 'notes',)
    list_filter = ('entity',)
    inlines = [
        TagInline,
    ]
    ordering = ('name',)
    readonly_fields = ('name', 'entity',)
    search_fields = ('name', 'notes',)

    class Media:
        css = {
            'all': ('code_exec.css',),
        }
        js = ("jquery.cookie.js", "code_exec.js",)
            
    def tag_count(self, obj):
        return obj.tags.count()
    tag_count.short_description = 'Defined Tags'
    
    def datasets(self, obj):
        ds = [desc for id,desc in obj.get_datasets()]
        ds.sort()   # make them in a consistent order
        return ", ".join(ds)
    tag_count.short_description = 'Available in' 

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

