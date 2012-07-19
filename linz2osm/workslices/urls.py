from django.conf.urls.defaults import *

urlpatterns = patterns('linz2osm.workslices.views',
                       (r'(?P<workslice_id>\w+)/show$', 'show_workslice'),
                       )
