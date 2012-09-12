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

if [ $# -lt 1 ]
then
    echo "Usage: load_dataset.sh <file.mp>"
    exit 1
fi

original_dir=$(pwd)
srid='EPSG:4326'
mpfile_path=$(pwd)/$1
mpfile_name=`basename $1`
mpfile_base=`basename $1 .mp`

dataset_db=nzopengps_`echo ${mpfile_base} | sed -e 's/-/_/' -e 's/\(.\)/\L\1/g' -e 's/\([^a-z0-9]\)/_/g'`
echo "Creating database ${dataset_db}"
dropdb ${dataset_db}
createdb ${dataset_db} -T template_postgis

echo "Converting file: ${mpfile_path}"
python `dirname $0`/mp2postgis.py ${mpfile_path} > /tmp/linz2osm_mp2postgis.sql

echo "Loading into database: ${dataset_db}"
psql ${dataset_db} -f /tmp/linz2osm_mp2postgis.sql > /dev/null
