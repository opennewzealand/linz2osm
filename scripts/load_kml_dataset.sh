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


if [ $# -lt 1 ]
then
    echo "Usage: load_kml_dataset.sh <directory1>"
    exit 1
fi

dataset_base=`basename $1`
echo "Loading directory: ${dataset_base}"
dataset_db=`echo ${dataset_base} | sed -e 's/\(.\)/\L\1/g' -e 's/\([^a-z0-9]\)/_/g'`
echo "Will use database ${dataset_db}"
dropdb ${dataset_db}
createdb ${dataset_db} -T template_postgis

for kmlfile in $1/*.kml
do
    echo "${kmlfile}"
    ogr2ogr -append -f PostgreSQL PG:dbname=${dataset_db} -lco LAUNDER=yes ${kmlfile} -a_srs EPSG:4326 -s_srs EPSG:4326
done
