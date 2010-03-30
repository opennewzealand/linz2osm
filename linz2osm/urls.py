from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

if settings.DEBUG:
    urlpatterns = patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )
else:
    urlpatterns = patterns('')

urlpatterns += patterns('',
    (r'data_dict/tag/eval/$', 'data_dict.views.tag_eval'),
    (r'convert/', include('linz2osm.convert.urls')),

    (r'^doc/', include('django.contrib.admindocs.urls')),
    (r'', include(admin.site.urls)),
)
