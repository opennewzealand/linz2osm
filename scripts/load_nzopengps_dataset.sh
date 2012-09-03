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
#
#
#  REQUIREMENTS
# 
#  pgdbf: install with e.g. apt-get install pgdbf
#
#  wine: install with e.g. apt-get install wine
#
#  you need to download gGPSmapper freeware and extract it into a directory.
#  Set cgpsmapper_dir to that directory.
#
#  You also need a working directory to extract the shapefiles into.
#  Set it with shapefile_working_dir

cgpsmapper_dir="/home/sdavis/winapps/cgpsmapper"
shapefile_working_dir="/tmp/linz2osm/load_nzopengps_dataset/working"

# Do not edit below here

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
mpfile_outdir=${shapefile_working_dir}/${mpfile_base}

echo "Converting file: ${mpfile_path}"
echo "Output directory: ${mpfile_outdir}"
mkdir -p ${mpfile_outdir}
cd ${mpfile_outdir}
wine ${cgpsmapper_dir}/cgpsmapper.exe SHP ${mpfile_path}
cd ${original_dir}

dataset_db=nzopengps_`echo ${mpfile_base} | sed -e 's/-/_/' -e 's/\(.\)/\L\1/g' -e 's/\([^a-z0-9]\)/_/g'`
echo "Creating database ${dataset_db}"
dropdb ${dataset_db}
createdb ${dataset_db} -T template_postgis

echo "Loading directory: ${mpfile_outdir}"

for shapefile in ${mpfile_outdir}/*.shp
do
    echo "${shapefile}"
    ogr2ogr -overwrite -f PostgreSQL PG:dbname=${dataset_db} -lco OVERWRITE=yes -lco LAUNDER=yes ${shapefile} -a_srs $srid -s_srs $srid
done

for dbfile in routing.dbf restrict.dbf
do
    echo "${dbfile}"
    pgdbf ${mpfile_outdir}/${dbfile} | psql ${dataset_db}
done
