from django.conf.urls.defaults import *

urlpatterns = patterns('linz2osm.data_dict.views',
                       (r'^tag/eval/$', 'tag_eval'),
                       (r'^layer/(?P<object_id>\w+)/stats/$', 'layer_stats'),
                       (r'^dataset/(?P<dataset_id>\w+)/$', 'show_dataset'),
                       (r'^field_stats/(?P<dataset_id>\w+)/(?P<layer_id>\w+)/(?P<field_name>\w+)/$', 'field_stats'),
                       )
