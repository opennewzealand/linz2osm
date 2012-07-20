from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib.gis import admin

admin.autodiscover()

if settings.DEBUG:
    urlpatterns = patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )
else:
    urlpatterns = patterns('')

urlpatterns += patterns('',
    (r'^data_dict/tag/eval/$', 'linz2osm.data_dict.views.tag_eval'),
    (r'^data_dict/layer/(?P<object_id>\w+)/stats/$', 'linz2osm.data_dict.views.layer_stats'),
    (r'^convert/', include('linz2osm.convert.urls')),
    (r'^workslices/', include('linz2osm.workslices.urls')),
    (r'^doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^/?$', 'linz2osm.lobby.views.home_page'),
)
