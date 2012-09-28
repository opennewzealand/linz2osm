#  LINZ-2-OSM
#  Copyright (C) 2010-2012 Koordinates Ltd.
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

from django.contrib import admin

from linz2osm.workslices.models import Workslice


class WorksliceAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'checked_out_at', 'layer', 'user', 'dataset',)
    ordering = ('id',)
    readonly_fields = ('name', 'checked_out_at', 'status_changed_at', 'layer_in_dataset','checkout_extent','feature_count', 'file_size',)
    save_on_top = True

    def layer(self, obj):
        return obj.layer_in_dataset.layer.name

    def dataset(self, obj):
        return obj.layer_in_dataset.dataset.description

admin.site.register(Workslice, WorksliceAdmin)
