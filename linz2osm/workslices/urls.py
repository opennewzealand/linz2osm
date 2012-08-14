from django.conf.urls.defaults import *

urlpatterns = patterns('linz2osm.workslices.views',
                       (r'list/$', 'list_workslices'),
                       (r'list/(?P<username>\w+)/$', 'list_workslices'),
                       (r'(?P<workslice_id>\w+)/show/$', 'show_workslice'),
                       (r'(?P<workslice_id>\w+)/update/$', 'update_workslice'),
                       (r'create/layer_in_dataset/(?P<layer_in_dataset_id>\w+)/$', 'create_workslice'),
                       (r'info/layer_in_dataset/(?P<layer_in_dataset_id>\w+)/$', 'workslice_info'),
                       )
