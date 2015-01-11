#!/usr/bin/env bash
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


if [ $# -lt 5 ]
then
    echo "Usage: load_lds_dataset.sh {initial|update} <database> <layer_id> <layer_name> <lds_key> [<viewparams> [<filter>]]"
    echo "Args were $@"
    exit 1
fi

# viewparams are e.g. from:2012-10-12T20:22:22.940122;to:2012-10-26T20:24:26.570496

dataset_db=$2
layer_name=$4
layer_id="v:x${3}-changeset"
wfs_server="http://wfs.data.linz.govt.nz" # Production
lds_key=$5 

wfs_cmd="${wfs_server}/${lds_key}/v/x${3}-changeset/wfs?SERVICE=WFS&VERSION=1.1.0&typeName=${layer_id}"

# Add <viewparams>
if [ "${6}" ]
    then
    wfs_cmd="${wfs_cmd}&viewparams=${6}"
fi

# Add <filter>
if [ "${7}" ]
    then
    wfs_cmd="${wfs_cmd}&CQL_FILTER=${7}"
fi

lcopts="-lco LAUNDER=yes -lco OVERWRITE=yes"

#srs="EPSG:4326"
#srs_options="-a_srs ${srs} -s_srs ${srs}"
srs_options=""

table_name=`echo ${layer_name} | sed -e 's/\(.\)/\L\1/g' -e 's/\([^a-z0-9]\)/_/g'`
echo "++++++++++++++++++++++++++++++++++++++++++++++++++"
echo "Using server ${wfs_cmd}"
echo "Loading layer: ${layer_name} into ${table_name} in ${dataset_db}"
echo "++++++++++++++++++++++++++++++++++++++++++++++++++"
echo 
# dropdb ${dataset_db}
# createdb ${dataset_db} -T template_postgis

# FIXME: update, not overwrite
echo "ogr2ogr -overwrite -f PostgreSQL PG:dbname=${dataset_db} ${lcopts} \"WFS:${wfs_cmd}\" ${srs_options} -nln ${table_name} "
echo "++++++++++++++++++++++++++++++++++++++++++++++++++"
echo 
ogr2ogr -overwrite -f PostgreSQL PG:dbname=${dataset_db} ${lcopts} "WFS:${wfs_cmd}" ${srs_options} -nln ${table_name} 

if [ "${1}" == "initial" ]
    then
    psql ${dataset_db} -c "ALTER TABLE ${table_name} DROP COLUMN \"__change__\";"
fi

psql ${dataset_db} -c "ALTER TABLE ${table_name} DROP COLUMN ogc_fid;"
psql ${dataset_db} -c "ALTER TABLE ${table_name} ADD PRIMARY KEY (id);"
