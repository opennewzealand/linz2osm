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

def osm_conflicts_query(workslice_features, query_data):
    return "".join(("[out:json];\n(\n",
                    "\n".join([wf.osm_conflicts_query_ql(query_data) for wf in workslice_features]),
                    "\n);\nout;\n",))
    
def osm_conflicts_json(workslice_features, query_data):
    r = requests.post(OVERPASS_API_URL, data={
            'data': osm_conflicts_query(workslice_features, query_data)
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


                  
