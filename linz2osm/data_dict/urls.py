#  LINZ-2-OSM
#  Copyright (C) Koordinates Ltd.
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls import patterns

urlpatterns = patterns('linz2osm.data_dict.views',
                       (r'^tag/eval/$', 'tag_eval'),
                       (r'^dataset/(?P<dataset_id>\w+)/update$', 'update_dataset'),
                       (r'^dataset/(?P<dataset_id>\w+)/merge_deletions$', 'merge_deletions_from_dataset'),
                       (r'^dataset/(?P<dataset_id>\w+)/$', 'show_dataset'),
                       (r'^field_stats/(?P<dataset_id>\w+)/(?P<layer_id>\w+)/(?P<field_name>\w+)/$', 'field_stats'),
                       (r'^layer/(?P<layer_id>\w+)/info/$', 'layer_notes'),
                       (r'^layer/(?P<layer_id>\w+)/stats/$', 'layer_stats'),
                       (r'^layer/(?P<layer_id>\w+)/preview/$', 'preview'),
                       (r'^layer/(?P<layer_id>\w+)/tagging/$', 'show_tagging'),
                       (r'^export/$', 'export_data_dict'),
                       )
