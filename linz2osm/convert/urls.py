from django.conf.urls.defaults import *

urlpatterns = patterns('linz2osm.convert.views',
    (r'data/$', 'layer_data'),
)
