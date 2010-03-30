from django.conf.urls.defaults import *

urlpatterns = patterns('linz2osm.convert.views',
    (r'(?P<dataset_id>\w+)/(?P<layer_name>\w+)/$', 'layer_data_export'),

    (r'$', 'layer_data'),
)
