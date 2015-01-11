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

urlpatterns = patterns('linz2osm.workslices.views',
                       (r'list/$', 'list_workslices'),
                       (r'list/(?P<username>\w+)/$', 'list_workslices'),
                       (r'(?P<workslice_id>\w+)/show/$', 'show_workslice'),
                       (r'(?P<workslice_id>\w+)/update/$', 'update_workslice'),
                       (r'create/layer_in_dataset/(?P<layer_in_dataset_id>\w+)/$', 'create_workslice'),
                       (r'info/layer_in_dataset/(?P<layer_in_dataset_id>\w+)/$', 'workslice_info'),
                       )
