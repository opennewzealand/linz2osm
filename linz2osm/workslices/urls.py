from django.conf.urls.defaults import *

urlpatterns = patterns('linz2osm.workslices.views',
                       (r'(?P<workslice_id>\w+)/show/$', 'show_workslice'),
                       (r'create/layer_in_dataset/(?P<layer_in_dataset_id>\w+)/$', 'create_workslice'),
                       )
