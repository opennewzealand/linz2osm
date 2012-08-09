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
    # FIXME: put into linz2osm.dataIdict.urls
    (r'^data_dict/tag/eval/$', 'linz2osm.data_dict.views.tag_eval'),
    (r'^data_dict/layer/(?P<object_id>\w+)/stats/$', 'linz2osm.data_dict.views.layer_stats'),
    (r'^data_dict/dataset/(?P<dataset_id>\w+)/$', 'linz2osm.data_dict.views.show_dataset'),
    # (r'^data_dict/layer/(?P<object_id>\w+)/$', 'linz2osm.data_dict.views.show_layer'),
    (r'^workslices/', include('linz2osm.workslices.urls')),
    (r'^doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^/?$', 'linz2osm.lobby.views.home_page'),
    (r'^login/', 'linz2osm.lobby.views.login'),
    (r'^logout/', 'linz2osm.lobby.views.logout'),
)
