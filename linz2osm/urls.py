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
    (r'^data_dict/', include('linz2osm.data_dict.urls')),
    (r'^workslices/', include('linz2osm.workslices.urls')),
    (r'^doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^/?$', 'linz2osm.lobby.views.home_page'),
    (r'^login/', 'linz2osm.lobby.views.login'),
    (r'^logout/', 'linz2osm.lobby.views.logout'),
)
