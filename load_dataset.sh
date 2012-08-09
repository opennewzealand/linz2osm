#!/usr/bin/env bash

if [ $# -lt 1 ]
then
    echo "Usage: load_dataset.sh <directory1> [<directory2> ...]"
    exit 1
fi

for dataset_dir in "$@"
do
    dataset_base=`basename ${dataset_dir}`
    echo "Loading directory: ${dataset_base}"
    dataset_db=`echo ${dataset_base} | sed -e 's/\(.\)/\L\1/g' -e 's/\([^a-z0-9]\)/_/g'`
    echo "Will use database ${dataset_db}"
    dropdb ${dataset_db}
    createdb ${dataset_db} -T template_postgis

    for shapefile in ${dataset_dir}/*.shp
    do
        if [ "`basename ${shapefile}`" = "contour.shp" ]
        then
            continue
        fi
        echo "${shapefile}"
        ogr2ogr -overwrite -f PostgreSQL PG:dbname=${dataset_db} -lco OVERWRITE=yes -lco LAUNDER=yes ${shapefile}
    done
done
