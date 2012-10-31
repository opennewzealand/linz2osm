#!/usr/bin/env bash
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


if [ $# -lt 3 ]
then
    echo "Usage: load_lds_dataset.sh <database> <layer_id> <layer_name> [<filter>]"
    exit 1
fi

dataset_db=$1
layer_name=$3
layer_id="v:x$2"
wfs_server="http://wfs.data.linz.govt.nz/cd067d1e5bd54e42bacfb9c19942737d/v/x${2}/wfs?SERVICE=WFS&VERSION=1.1.0&TYPENAME=${layer_id}"
if [ "${4}" ]
    then
    wfs_server="${wfs_server}&CQL_FILTER=${4}"
fi
srs="EPSG:4326"

table_name=`echo ${layer_name} | sed -e 's/\(.\)/\L\1/g' -e 's/\([^a-z0-9]\)/_/g'`
echo "Using server ${wfs_server}"
echo "Loading layer: ${layer_name} into ${table_name} in ${dataset_db}"
# dropdb ${dataset_db}
# createdb ${dataset_db} -T template_postgis

# FIXME: update, not overwrite
ogr2ogr -overwrite -f PostgreSQL PG:dbname=${dataset_db} -lco OVERWRITE=yes -lco LAUNDER=yes "WFS:${wfs_server}" -progress -a_srs ${srs} -s_srs ${srs} -nln ${table_name} 
