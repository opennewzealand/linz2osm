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

import urllib
import requests
from django.contrib.gis.geos import GEOSGeometry, Point, LineString
from linz2osm.workslices.models import *

OVERPASS_API_URL = "http://overpass.osm.rambler.ru/cgi/interpreter?data="
OVERPASS_PROXIMITY = 0.001

def str_bounds_for(geobounds):
    return "(%f,%f,%f,%f)" % (
        geobounds[1] - OVERPASS_PROXIMITY,
        geobounds[0] - OVERPASS_PROXIMITY,
        geobounds[3] + OVERPASS_PROXIMITY,
        geobounds[2] + OVERPASS_PROXIMITY,
        )

def osm_node_match_query(layer_in_dataset, data_table):
    return "[out:json];\n(\n" + "\n".join([osm_node_match_query_ql(layer_in_dataset, row_data) for row_data, row_geom in data_table]) + "\n);\nout;\n"

def osm_node_match_json(layer_in_dataset, data_table):
    query = osm_node_match_query(layer_in_dataset, data_table)
    print "-----=====+++ < ( [ { XXX OVERPASS QUERY XXX } ] ) > +++=====-----"
    print query
    r = requests.post(OVERPASS_API_URL, data={
            'data': query
            })
    return r.json

def osm_node_match_query_ql(layer_in_dataset, row_data):
    layer = layer_in_dataset.layer
    geotype = layer.geometry_type
    if geotype != "LINESTRING":
        raise Error("Cannot do node matching for %s" % geotype)
    
    return "\n".join([osm_node_match_query_ql_for_field(layer_in_dataset, layer.special_node_tag_name, v, row_data['dataset_name'], row_data['dataset_version'], ) for v in [
                row_data[layer.special_start_node_field_name],
                row_data[layer.special_end_node_field_name],
                ]])

def osm_node_match_query_ql_for_field(layer_in_dataset, field_tag_name, field_value, dataset_name, dataset_version):
    layer = layer_in_dataset.layer
    return dedent("""
            node
            ["%(node_tag)s"="%(node_value)s"]
            ["%(dataset_name_tag)s"="%(dataset_name_value)s"]
            %(str_bounds)s
            ;
            """ % {
            # ["%(dataset_version_tag)s"="%(dataset_version_value)s"];
            'node_tag': field_tag_name,
            'node_value': field_value,
            'dataset_name_tag': layer.special_dataset_name_tag,
            'dataset_name_value': dataset_name,
            'dataset_version_tag': layer.special_dataset_version_tag,
            'dataset_version_value': dataset_version,
            'str_bounds': str_bounds_for(layer_in_dataset.extent.extent),
            })

def osm_conflicts_query(workslice_features, tags_ql):
    return "".join(("[out:json];\n(\n",
                    "\n".join([wf.osm_conflicts_query_ql(tags_ql) for wf in workslice_features]),
                    "\n);\nout;\n",))
    
def osm_conflicts_json(workslice_features, tags_ql):
    r = requests.post(OVERPASS_API_URL, data={
            'data': osm_conflicts_query(workslice_features, tags_ql)
            })
    return r.json

def osm_geojson(osm_features, nodes={}, ways={}):
    return dedent("""
            { "type": "FeatureCollection",
              "features": [%s],
              "crs": {
                  "type" : "name",
                  "properties" : {
                      "name" : "EPSG:4326"
                  }
              }
            }
        """ % ",".join(filter(None, [osm_feature_geojson(of, nodes, ways) for of in osm_features])))

def osm_feature_geojson(osm_feature, nodes={}, ways={}):
    geom = geometry_for_osm_feature(osm_feature, nodes, ways)
    if not geom:
        return None
    return """
              {
              "geometry": %s,
              "type": "Feature",
              "properties": {
                  "model": "OsmFeature"
              } } """ % geom.geojson

def geometry_for_osm_feature(osm_feature, nodes={}, ways={}):
    if osm_feature['type'] == 'way':
        node_list = filter(None, [
                node_point(node_id, nodes) for node_id in osm_feature['nodes']
                ])
        if node_list:
            return LineString(node_list)
        else:
            return None
    elif osm_feature['type'] == 'node':
        return Point(osm_feature['lon'], osm_feature['lat'])
    elif osm_feature['type'] == 'rel':
        # FIXME - implement
        return None
    else:
        return None

def node_point(node_id, nodes):
    n = nodes.get(node_id)
    if n:
        return Point(n['lon'], n['lat'])
    else:
        return None


                  
