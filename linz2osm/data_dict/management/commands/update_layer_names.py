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

from django.core.management.base import BaseCommand
from django.db import transaction, connection, connections

from linz2osm.data_dict.models import Layer, LayerInDataset, Dataset, Tag

RENAMES = {
    'breakwtr_cl': 'breakwater_cl',
    'cattlstp_pnt': 'cattlestop_pnt',
    'cblwy_ind_cl': 'cableway_industrial_cl',
    'cblwy_peo_cl': 'cableway_people_cl',
    'descrip_text': 'descriptive_text',
    'dredg_tl_cl': 'dredge_tailing_cl',
    'embankmnt_cl': 'embankment_cl',
    'ferry_cr_cl': 'ferry_crossing_cl',
    'fish_fm_poly': 'fish_farm_poly',
    'floodgte_pnt': 'floodgate_pnt',
    'gas_val_pnt': 'gas_valve_pnt',
    'geo_name': 'geographic_name',
    'gl_lake_poly': 'glacial_lake_poly',
    'golf_crs_pnt': 'golf_course_pnt',
    'golf_crs_poly': 'golf_course_poly',
    'grav_pit_poly': 'gravel_pit_poly',
    'hist_ste_pnt': 'historic_site_pnt',
    'ice_clf_edge': 'ice_cliff_edge',
    'ice_strm_cl': 'ice_stream_pnt',
    'marne_fm_cl': 'marine_farm_cl',
    'marne_fm_poly': 'marine_farm_poly',
    'melt_strm_cl': 'melt_stream_cl',
    'moran_wl_poly': 'moraine_wall_poly',
    'pumce_pt_poly': 'pumice_pit_poly',
    'racetrk_cl': 'racetrack_cl',
    'racetrk_pnt': 'racetrack_pnt',
    'racetrk_poly': 'racetrack_poly',
    'radar_dm_pnt': 'radar_dome_pnt',
    'rail_stn_pnt': 'rail_station_pnt',
    'reservr_poly': 'reservoir_poly',
    'res_area_poly': 'residential_area_poly',
    'rifle_rg_poly': 'rifle_range_poly',
    'rock_out_pnt': 'rock_outcrop_pnt',
    'sat_stn_pnt': 'satellite_station_pnt',
    'scatscrb_poly': 'scattered_scrub_poly',
    'shelt_blt_cl': 'shelter_belt_cl',
    'showgrd_poly': 'showground_poly',
    'spillwy_edge': 'spillway_edge',
    'sprtfld_poly': 'sportsfield_poly',
    'telephn_cl': 'telephone_cl',
    'waterfal_edg': 'waterfall_edge',
    'waterfal_cl': 'waterfall_cl',
    'waterfal_pnt': 'waterfall_pnt',
    'waterfal_poly': 'waterfall_poly',
    'water_r_cl': 'water_race_cl',
}

class Command(BaseCommand):
    help = "Rename layers with old abbreviated names"

    def handle(self, **options):
        # drop existing layers with new names: only needed if you've run dd_load
        # before update_layer_names
        # for new_name in RENAMES.values():
        #    for l in Layer.objects.filter(name=new_name):
        #        l.delete()

        with transaction.commit_on_success():
            cursor = connection.cursor()
            for old_name, new_name in RENAMES.iteritems():
                cursor.execute("UPDATE data_dict_layer SET name = %s WHERE name = %s;", [new_name, old_name])
                cursor.execute("UPDATE data_dict_tag SET layer_id = %s WHERE layer_id = %s;", [new_name, old_name])
                cursor.execute("UPDATE data_dict_layerindataset SET layer_id = %s WHERE layer_id = %s;", [new_name, old_name])

            print 'CONNECTION: default'
            for q in connection.queries:
                print q['sql']

        # the actual layers
        for conn_name in connections:
            if conn_name != 'default':
                conn = connections[conn_name]
                with transaction.commit_on_success():
                    cursor = conn.cursor()
                    for old_name, new_name in RENAMES.iteritems():
                        cursor.execute("UPDATE geometry_columns SET f_table_name = %s WHERE f_table_name = %s;", [new_name, old_name])
                        cursor.execute("SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename=%s;", [old_name])
                        old_table_exists = cursor.fetchall()
                        if old_table_exists:
                            print "In %s renaming %s to %s" % (conn_name, old_name, new_name)
                            cursor.execute("ALTER TABLE %s RENAME TO %s;" % (old_name, new_name))
                print 'CONNECTION: %s' % (conn_name,)
                for q in conn.queries:
                    print q['sql']
