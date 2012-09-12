#!/usr/bin/python
# mp2postgis.py
# adapted from mp2osm_linz_jr_pl.py by Stephen Davis (steve@koordinates.com), which in turn was
# derived from 'mp2osm_ukraine.py'
# modified by simon@mungewell.org
# modified by Karl Newman (User:SiliconFiend) to preserve routing topology and parse RouteParam
# modified by Joe Richards (joe@penski.net) to include SUFI IDs and support most LINZ/NZOGPS feature types
# modified by Peter Lambrechtsen (plambrechtsen@gmail.com) to have a correctly formatted xml that will be imported by osmosis, and to handle larger MP files.
# license: GPL V2 or later
# if you make modifications, please email your version to the previous authors (as per the GPL)

import sys
import datetime
import re

from textwrap import dedent

SRID = 4326
PKEY = "serial PRIMARY KEY"
VARCHAR = "character varying(255)"
FLAG_DEF_FALSE = "boolean NOT NULL DEFAULT FALSE"

# Define the mapping from Garmin type codes to OSM tags
# Note that single items in parentheses need a trailing comma
poitagmap = {
     #JR: catCities
     (0x0100,0x100): {'place': 'city', 'linz:comment': 'size >10M'},        # added by JR.  np
     (0x0200,0x200): {'place': 'city', 'linz:comment': 'size 5-10M'},      # added by JR.  np
     (0x0300,0x300): {'place': 'city', 'linz:comment': 'size 2-5M'},       # added by JR.  np
     (0x0400,0x400): {'place': 'city', 'linz:comment': 'size 1-2M'},       # added by JR - pres
     (0x0500,0x500): {'place': 'city', 'linz:comment': 'size 0.5-1M'},     # added by JR - pres
     (0x0600,0x600): {'place': 'city', 'linz:comment': 'size 200-500K'},   # added by JR - pres
     (0x0700,0x700): {'place': 'city', 'linz:comment': 'size 100-200K'},   # added by JR - pres
     (0x0800,0x800): {'place': 'city', 'linz:comment': 'size 50-100K'},    # added by JR - pres
     (0x0900,0x900): {'place': 'city', 'linz:comment': 'size 20-50K'},     # added by JR - pres
     (0x0a00,0xa00): {'place': 'town', 'linz:comment': 'size 10-20K'},     # added by JR - pres
     (0x0b00,0xb00): {'place': 'town', 'linz:comment': 'size 5-10K'},       # added by JR - pres
     (0x0c00,0xc00): {'place': 'town', 'linz:comment': 'size 2-5K'},       # added by JR - pres
     (0x0d00,0xd00): {'place': 'town', 'linz:comment': 'size 1-2K'},       # added by JR - pres
     (0x0e00,0xe00): {'place': 'village', 'linz:comment': 'size 500-1K'},  # added by JR - pres
     (0x0f00,0xf00): {'place': 'village', 'linz:comment': 'size 200-500'}, # added by JR - pres
     (0x1000,): {'place': 'hamlet', 'linz:comment': 'size 100-200'},  # added by JR - pres
     (0x1100,): {'place': 'hamlet', 'linz:comment': 'size 100-200'},  # added by JR - pres

     (0x1200,): {'leisure': 'marina' },                               # added by JR - Raglan Wharf.  Spreadsheet suggests hamlet (0-100 size) but not in our dataset

     (0x1612, 0x1c00, 0x6400): {'highway': 'gate'},
     (0x160f,): {'man_made': 'beacon', 'mark_type': 'white'},         # added by JR - pres

     (0x1c01,): {'man_made': 'ship_wreck'},                           # added by JR - pres
     (0x1c09,): {'linz:comment': 'FIXMEFIXME  rock, awash, reef'},                   # added by JR - pres - TODO ammend

     (0x1e00,): {'place': 'region'},                                  # added by JR - pres, e.g. Southland    
     (0x2b00,): {'tourism': 'hotel'},
     (0x2b01,): {'tourism': 'motel'},
     (0x2b03,): {'tourism': 'caravan_site'},
     (0x2c06,): {'leisure': 'park'}, # added by JR
     (0x2c08,): {'leisure': 'park'}, # added by JR
     (0x2d05,): {'leisure': 'golf_course'}, # added by JR
     (0x2d06,): {'sport': 'skiing'}, # added by JR
     (0x2f04,): {'aeroway': 'aerodrome'}, # added by JR
     (0x2e02,): {'shop': 'supermarket'},
     (0x2f08,): {'amenity': 'bus_station'},
     (0x2f09,): {'waterway': 'boatyard'}, # added by JR
     (0x3002,): {'amenity': 'hospital'}, # added by JR
     (0x4400,): {'amenity': 'fuel'},
     (0x4700,): {'leisure': 'slipway'},
     (0x4800,): {'tourism': 'campsite'},
     (0x4900,): {'leisure': 'park'},
     (0x4a00,): {'tourism': 'picnic_site'},
     (0x4c00,): {'tourism': 'information'},
     (0x4d00,): {'amenity': 'parking'},
     (0x4e00,): {'amenity': 'toilets'},
     (0x5100,): {'amenity': 'telephone'},
     (0x5200,): {'tourism': 'viewpoint'},
     (0x5400,): {'sport': 'swimming'},
     (0x5500,): {'waterway': 'dam'}, # added by JR
     (0x5904,): {'aeroway': 'helipad'},
     (0x5905,): {'aeroway': 'aerodrome'},
     (0x5904,): {'aeroway': 'helipad'},
     (0x5a00,): {'distance_marker': 'yes'}, # Not approved
     (0x6401,): {'bridge': 'yes'}, # Apply to points?
     (0x6401,): {'building': 'yes'},
     (0x6402,): {'amenity': 'shelter', 'building': 'yes', 'tourism': 'alpine_hut'}, # added by JR -trekking huts, bivouacs, shelters, cabins
     (0x6403,): {'amenity': 'grave_yard'}, #added by JR
     (0x6505,): {'amenity': 'public_building', 'building': 'yes'},  # added by JR, only ex is Pumphouse
     (0x6406,): {'mountain_pass': 'yes', 'place': 'locality'}, # by JR: was highway=crossing, now mountain_pass=yes (for pass,col,saddle) TODO check
     (0x640c,): {'man_made': 'mineshaft'},
     (0x640a,): {'place': 'locality'}, # by JR - seems to apply to a lot of diff features, and is Garmin default for a POI
     (0x640d,): {'man_made': 'pumping_rig', 'type': 'oil'},
     (0x6411,): {'man_made': 'tower'},
     (0x6412,): {'highway': 'track', 'place': 'locality'}, # by JR - start of trek/walk- used to be 'trailhead' which is not even a proposed value
     (0x6413,): {'natural': 'cave_entrance'}, # by JR - used to be tunnel=yes but appears to caves - TODO check
     (0x6500, 0x650d): {'natural': 'water'},
     (0x6501,): {'natural': 'glacier'}, # added by JR - TODO tourism=attraction too?
     (0x6508,): {'waterway': 'waterfall'},
     (0x650c,): {'place': 'islet'},  # added by JR - v2
     (0x6511,): {'natural': 'spring'}, # added by JR - natural spring source
     (0x6513,): {'natural': 'wetland'}, # added by JR
     (0x6600,): {'place': 'locality', 'natural': 'hill', 'linz:comment': 'FIXME - hill?'}, # added by JR.. TODO check these, most seem to be in northland
     (0x6603,): {'landuse':'basin'}, # added by JR - TODO check since this is natural basin poi
     (0x6605,): {'natural': 'bench'},
     (0x6607,): {'natural': 'cliff'}, # added by JR - cliffs, bluffs etc
     (0x660c,): {'place': 'island'}, # added by JR - seems to be small islands as well as large
     (0x660a,): {'natural': 'wood'}, # added by JR - include bush and wild overgrowth
     (0x6611,): {'natural': 'mountain_range'}, # added by JR - TODO does not exist as tag
     (0x6613,): {'natural': 'ridge'}, # added by JR - TODO does not exist as tag

     (0x660d,): {'place': 'locality', 'natural': 'water'}, # added by JR - poi which are lake names
     (0x6616,): {'natural': 'peak'},
     (0x6617,): {'place': 'locality', 'natural': 'gully', 'linz:comment': 'FIXME: gorge/gully'}, # added by JR - gully/gorge does not exist, but giving it a placename might work
    }
polylinetagmap = {
     # TODO FIXME all these highway types, and links need to be checked
     (0x1,): {'highway': 'motorway'},   # added by JR
     (0x2,): {'highway': 'trunk'},
     (0x3,): {'highway': 'primary'},
     (0x4,): {'highway': 'secondary'},
     (0x5,): {'highway': 'tertiary'},
     (0x6,): {'highway': 'residential'},
     (0x7,): {'highway': 'service'}, # added by JR - TODO confirm in other places, example is Auckland airport's Cyril Kay Rd.. cf 0x7 as polygon which is diff.
     (0x8,): {'highway': 'primary_link'}, # added by JR - TODO FIXME what is a turning point (U-Turn etc) on a big road? this is actually on a tertiary road when i looked
     (0x9,): {'highway': 'secondary_link'}, # added by JR - TODO FIXME in the LINZ dataset is this actually used to connect secondary roads, or other types?
     (0xa,): {'highway': 'track', 'surface': 'unpaved'},
     (0xb,): {'highway': 'trunk_link'}, # added by JR
     (0xc,): {'junction': 'roundabout'}, # added by JR
     (0xd,): {'highway': 'cycleway'}, # added by JR
     (0x14,): {'railway': 'rail'}, # added by JR
     (0x16,): {'highway': 'footway'}, # added by JR
     (0x18,): {'waterway': 'stream'},
     (0x1b,): {'route': 'ferry'}, # added by JR

     # boundaries http://wiki.openstreetmap.org/wiki/Key:admin_level#10_admin_level_values_for_specific_countries
     (0x1c,): {'boundary': 'administrative', 'admin_level': '4'}, # added by JR, seems to be e.g. Otago/Canterbury, Auckland/Waikato TODO check this
     (0x1d,): {'boundary': 'administrative', 'admin_level': '6'}, # added by JR, seems to be e.g. Timaru district council, TODO check this

     (0x1e,): {'landuse': 'forest', 'leisure': 'nature_reserve'}, # added by JR
     (0x1f,): {'waterway': 'canal'},                              # added by JR, was 'river', but the only ones present are in Chch canals
     (0x29,): {'power': 'line'}
    }
polygontagmap = {
     (0x2,): {'landuse': 'residential'},     # added by JR - pres
     (0x20,): {'tourism': 'zoo', 'tourism': 'attraction'}, # added by JR - only Hamilton Zoo
     (0x5,): {'amenity': 'parking', 'area': 'yes'},
     (0x7,): {'landuse': 'aeroway'}, # added by JR - to describe outlines of runways and airport areas, cf. polyline
     (0x8,): {'landuse': 'retail', 'building': 'shops'}, # added by JR, cf. 0x8 polyline which is a ramp
     (0xd,): {'landuse': 'reservation', 'area': 'yes'}, # reservation is not even a proposed value TODO JR: this looks weird to me
     (0x13,): {'building': 'yes', 'area': 'yes'}, # added by JR - buildings, including hospitals or other random ones, esp present in Waikato
     (0x14,0x15): {'natural': 'wood', 'area': 'yes'}, # added by JR - v2
     (0x17,): {'leisure': 'park', 'area': 'yes'}, # added by JR - city park
     (0x18,): {'leisure': 'golf_course', 'area': 'yes'},
     (0x19,): {'leisure': 'sports_centre', 'area': 'yes', 'linz:todo': 'check type'}, # added by JR, TODO (check, sports_centre implies a building, but is at least rendered green). examples found in LINZ include sports parks, race courses, stadiums, cricket 'domains'..
     (0x1a,): {'landuse': 'cemetery', 'area': 'yes'}, # added by JR, TODO is ok, or should it be amenity=graveyard
     (0x28,): {'comment': 'JR:ocean'}, # added by JR, TODO work out what this is about, should we using coastlines
     (0x3c, 0x3e, 0x40, 0x41): {'natural': 'water', 'area': 'yes'}, # 0x3e added by JR
     (0x47, 0x48, 0x49): {'waterway': 'riverbank', 'area': 'yes'}, # 0x47 added by JR
     (0x4c,): {'waterway': 'intermittent', 'area': 'yes'},
     (0x50,): {'natural': 'wood', 'area': 'yes'}, # added by JR, seems to be for nature reserves too
     (0x51,): {'natural': 'wetland', 'area': 'yes'} # added by JR, was marsh
    }

def esc_quotes(text):
    if text:
        return text.replace("'", "''")
    else:
        return text

def caps(words):
    return ' '.join([x.capitalize() for x in words.split()])

def xy_from_text(coords):
    lat, lon = coords.strip(" ()\n").split(",")
    return (lon, lat)

def sql_repr(obj):
    if isinstance(obj, str):
        return "'%s'" % esc_quotes(obj)
    elif isinstance(obj, bool):
        return str(obj).upper()
    elif isinstance(obj, datetime.date):
        return "DATE '%s'" % str(obj)
    elif isinstance(obj, tuple): # that is, a point. Maybe FIXME sometime.
        return "ST_GeomFromEWKT('SRID=%d;POINT(%s %s)')" % (SRID, obj[0], obj[1])
    elif isinstance(obj, list): # that is, a line. Maybe FIXME sometime.
        return "ST_GeomFromEWKT('SRID=%d;LINESTRING(%s)')" % (SRID, ",".join(["%s %s" % (x, y) for (x, y) in obj]))
    elif obj is None:
        return 'NULL'
    else:
        # this includes Polygon, int and float
        return str(obj)

class MPRecord(object):
    table_name = "mp_record"
    closing_tags = ("[END]",)
    columns = ()
    
    def __init__(self, mp_file, initial_info, *args, **kwargs):
        self.mp_file = mp_file
        self.record = initial_info.copy()
        super(MPRecord, self).__init__(*args, **kwargs)

    @classmethod    
    def table_creation_sql(cls):
        return dedent("""
            DROP TABLE IF EXISTS %(table_name)s CASCADE;
            CREATE TABLE %(table_name)s (%(columns_sql)s);
        """) % {
            'table_name': cls.table_name,
            'columns_sql': cls.columns_sql(),
            }

    @classmethod
    def columns_sql(cls):
        return ', '.join(["%s %s" % rec for rec in cls.columns if rec[0] != 'wkb_geometry'])

    @classmethod
    def closable_with(cls, line):
        return line.startswith(cls.closing_tags)
    
    def insert_sql(self):
        column_list = [cname for (cname, ctype) in self.columns if (self.record.get(cname) is not None)]
        values_list = [self.record.get(cname) for cname in column_list]
        
        return "INSERT INTO %(table_name)s (%(column_list)s) VALUES (%(values_list)s);\n" % {
            "table_name": self.table_name,
            "column_list": ', '.join(column_list),
            "values_list": ', '.join([sql_repr(c) for c in values_list]),
            }

    def handle_line(self, line):
        if line.strip() == "":
            pass
        else:
            return False
        return True
    
    def close_with_line(self, line):
        return True

class MPImgData(MPRecord):
    table_name = "mp_img"
    columns = MPRecord.columns + (
        ("id", PKEY),
        ("key", VARCHAR),
        ("val", "text"),
        )
    closing_tags = MPRecord.closing_tags + ("[END-IMG ID]",)
    
    def __init__(self, mp_file, initial_info, *args, **kwargs):
        self.img_items = []
        super(MPImgData, self).__init__(mp_file, initial_info, *args, **kwargs)

    def handle_line(self, line):
        if line.find("=") >= 0:
            key, value = line.strip().split("=")
            self.img_items.append((key, value,))
        else:
            return super(MPImgData, self).handle_line(line)
        return True

    def insert_sql(self):
        return "".join(["INSERT INTO %(table_name)s (key, val) VALUES ('%(key)s', '%(val)s');\n" % {
                    "table_name": self.table_name,
                    "key": esc_quotes(key),
                    "val": esc_quotes(val),
                    } for key, val in self.img_items])

class MPZipCodes(MPRecord):
    table_name = "mp_zipcode"
    columns = MPRecord.columns + (
        ("id", PKEY),
        ("zip", VARCHAR),
        )
    closing_tags = MPRecord.closing_tags + ("[END-ZipCodes]", "[END-ZIPCODES]")

    def __init__(self, mp_file, initial_info, *args, **kwargs):
        self.zipcodes = []
        super(MPZipCodes, self).__init__(mp_file, initial_info, *args, **kwargs)

    def handle_line(self, line):
        if line.startswith('ZipCode'):
            parts = line.split('=')
            self.zipcodes.append((int(parts[0].strip(" ZipCode")), parts[1].strip()))
        else:
            return super(MPZipCodes, self).handle_line(line)
        return True

    def insert_sql(self):
        return "".join(["INSERT INTO %(table_name)s (id, zip) VALUES (%(values_list)s);\n" % {
            "table_name": self.table_name,
            "values_list": "%s, '%s'" % zipcode,
            } for zipcode in self.zipcodes])
    
class MPCountries(MPRecord):
    table_name = "mp_country"
    columns = MPRecord.columns + (
        ("id", PKEY),
        ("abbrev", VARCHAR),
        ("label", VARCHAR),
        )
    closing_tags = MPRecord.closing_tags + ("[END-COUNTRIES]", "[END-Countries]",)

    country_re = re.compile('^Country(?P<idx>\d+)=(?P<name>[ 0-9A-Za-z\']+)(~\[0x1d\](?P<abbrev>\w+))?$')

    def __init__(self, mp_file, initial_info, *args, **kwargs):
        self.countries = []
        super(MPCountries, self).__init__(mp_file, initial_info, *args, **kwargs)

    def handle_line(self, line):
        if line.startswith('Country'):
            mdata = self.country_re.match(line.strip())
            if mdata:
                self.countries.append((mdata.group("idx"), mdata.group("abbrev"), esc_quotes(mdata.group("name"))))
        else:
            return super(MPCountries, self).handle_line(line)
        return True

    def insert_sql(self):
        return "".join(["INSERT INTO %(table_name)s (id, abbrev, label) VALUES (%(values_list)s);\n" % {
            "table_name": self.table_name,
            "values_list": "%s, '%s', '%s'" % country,
            } for country in self.countries])

class MPRegions(MPRecord):
    table_name = "mp_region"
    columns = MPRecord.columns + (
        ("id", PKEY),
        ("abbrev", VARCHAR),
        ("label", VARCHAR),
        ("country_id", "integer"),
        )
    closing_tags = MPRecord.closing_tags + ("[END-REGIONS]", "[END-Regions]",)

    region_re = re.compile('^Region(?P<idx>\d+)=(?P<name>[ 0-9A-Za-z\']+)(~\[0x1d\](?P<abbrev>\w+))?$')

    def __init__(self, mp_file, initial_info, *args, **kwargs):
        self.regions = []
        super(MPRegions, self).__init__(mp_file, initial_info, *args, **kwargs)

    def handle_line(self, line):
        if line.startswith('Region'):
            mdata = self.region_re.match(line.strip())
            if mdata:
                self.regions.append([mdata.group("idx"), mdata.group("abbrev"), esc_quotes(mdata.group("name")), None])
        # FIXME: Doesn't support regions in multiple countries
        elif line.startswith('CountryIdx'):
            country_id = line.split("=")[1].strip()
            self.regions[-1][3] = int(country_id)
        else:
            return super(MPRegions, self).handle_line(line)
        return True

    def insert_sql(self):
        return "".join(["INSERT INTO %(table_name)s (id, abbrev, label, country_id) VALUES (%(values_list)s);\n" % {
            "table_name": self.table_name,
            "values_list": ", ".join([sql_repr(v) for v in region]),
            } for region in self.regions])
    
class MPCities(MPRecord):
    table_name = "mp_city"
    columns = MPRecord.columns + (
        ("id", PKEY),
        ("label", VARCHAR),
        ("region_id", "integer"),
        )
    closing_tags = MPRecord.closing_tags + ("[END-CITIES]", "[END-Cities]",)

    city_re = re.compile('^City(?P<idx>\d+)=(?P<name>.+)$')

    def __init__(self, mp_file, initial_info, *args, **kwargs):
        self.cities = []
        super(MPCities, self).__init__(mp_file, initial_info, *args, **kwargs)

    def handle_line(self, line):
        if line.startswith('City'):
            mdata = self.city_re.match(line.strip())
            if mdata:
                self.cities.append([mdata.group("idx"), esc_quotes(mdata.group("name")), None])
        # FIXME: Doesn't support cities in multiple regions
        elif line.startswith('RegionIdx'):
            region_id = line.split("=")[1].strip()
            self.cities[-1][2] = int(region_id)
        else:
            return super(MPCities, self).handle_line(line)
        return True

    def insert_sql(self):
        return "".join(["INSERT INTO %(table_name)s (id, label, region_id) VALUES (%(values_list)s);\n" % {
            "table_name": self.table_name,
            "values_list": ", ".join([sql_repr(v) for v in city]),
            } for city in self.cities])

class MPRestrict(MPRecord):
    table_name = "mp_restrict"
    closing_tags = MPRecord.closing_tags + ("[END-RESTRICT]", "[END-Restrict]",)
    columns = MPRecord.columns + (
        ("id", PKEY),
        ("nod", "integer"),
        ("node_id_1", "integer"), # REFERENCES mp_node(id)
        ("node_id_2", "integer"), # REFERENCES mp_node(id)
        ("node_id_3", "integer"), # REFERENCES mp_node(id)
        ("node_id_4", "integer"), # REFERENCES mp_node(id)
        ("road_id_1", "integer"),
        ("road_id_2", "integer"),
        ("road_id_3", "integer"),
        ("not_for_emergency", FLAG_DEF_FALSE),
        ("not_for_goods", FLAG_DEF_FALSE),
        ("not_for_car", FLAG_DEF_FALSE),
        ("not_for_bus", FLAG_DEF_FALSE),
        ("not_for_taxi", FLAG_DEF_FALSE),
        ("not_for_foot", FLAG_DEF_FALSE),
        ("not_for_bicycle", FLAG_DEF_FALSE),
        ("not_for_truck", FLAG_DEF_FALSE),
        )

    def __init__(self, mp_file, initial_info, *args, **kwargs):
        super(MPRestrict, self).__init__(mp_file, initial_info, *args, **kwargs)

    def handle_line(self, line):
        if line.startswith("TraffPoints"):
            traff_points = line.split("=")[1].strip().split(",")[:4]
            for (counter, traff_point) in enumerate(traff_points):
                self.record["node_id_%d" % (counter + 1,)] = int(traff_point)
        elif line.startswith("TraffRoads"):
            traff_roads = line.split("=")[1].strip().split(",")[:3]
            for (counter, traff_road) in enumerate(traff_roads):
                self.record["road_id_%d" % (counter + 1,)] = int(traff_road)
        elif line.startswith("Nod"):
            self.record["nod"] = int(line.split("=")[1].strip())
        elif line.startswith("RestrParam"):
            vehicles = ['emergency', 'goods', 'car', 'bus', 'taxi', 'foot', 'bicycle', 'truck']
            restr_param = line.split("=")[1].strip().split(",")
            for veh, res in zip(vehicles, restr_param):
                if res.strip() == '1':
                    self.record['not_for_' + veh] = True
        else:
            return super(MPRestrict, self).handle_line(line)
        return True
            
class MPGeometry(MPRecord):
    table_name = "mp_geometry"
    geotype = "GEOMETRY"
    columns = MPRecord.columns + (
        ("type",          "numeric(5,0)"),
        ("marine",        "boolean"),
        ("label",         "text"),
        ("level",         "numeric(5,0)"),
        ("endlevel",      "numeric(5,0)"),
        ("linz_sufi",     "text"),
        ("linz_id",       "text"),
        ("created_date",  "date"),
        ("auto_numbered_date", "date"),
        ("wkb_geometry",  "geometry"), # Treated specially in columns_sql
        )
    
    def __init__(self, mp_file, initial_info, *args, **kwargs):
        super(MPGeometry, self).__init__(mp_file, initial_info, *args, **kwargs)

    @classmethod    
    def table_creation_sql(cls):
        return dedent("""
            DROP TABLE IF EXISTS %(table_name)s;
            CREATE TABLE %(table_name)s (%(columns_sql)s);
            SELECT AddGeometryColumn('%(table_name)s', 'wkb_geometry', %(srid)d, '%(geotype)s', 2);
        """) % {
            'table_name': cls.table_name,
            'columns_sql': cls.columns_sql(),
            'srid': SRID,
            'geotype': cls.geotype,
            }

    def handle_line(self, line):
        if line.startswith('Label'):
            label = line.split('=')[1].strip()
            # Now strip out control codes such as ~[0x2f]
            codestart = label.find('~[')
            if codestart != -1:
                codeend = label.find(']',codestart)
                if codeend != -1:
                    label = label[0:codestart] + ' ' + label[codeend+1:]
            self.record['label'] = caps(label.strip())
        elif line.startswith('Type'):
            typecode = int(line.split('=')[1].strip(), 16)
            self.record['type'] = typecode
            # FIXME
            # for codes, taglist in elementtagmap.iteritems():
            #     if typecode in codes:
            #         found=True
            #         for key, value in taglist.iteritems():
            #             tag = ET.Element('tag', k=key, v=value)
            #             tag.tail = '\n    '
            #             node.append(tag)
            # if found==False :
            #     print 'ptang missing 0x%x poi:%s line:%s poly:%s sufi:%s' % (typecode, poi, polyline, polygon, sufi)
            #     found=False;
        elif line.startswith('Marine'):
            marine = line.split('=')[1].strip()
            if marine == 'Y' or marine =='1':
                self.record['marine'] = True
        elif line.startswith('City'):
            city = line.split('=')[1].strip()
            if city == 'Y' or city =='1':
                self.record['city'] = True
        elif line.startswith('RoadID'):
            roadid = line.split('=')[1].strip()
            self.record['road_id'] = roadid
        elif line.startswith('EndLevel'):
            endlevel = line.split('=')[1].strip()
            self.record['endlevel'] = int(endlevel)
        else:
            return super(MPGeometry, self).handle_line(line)
        return True


class MPPoi(MPGeometry):
    table_name = "mp_poi"
    geotype = 'POINT'
    columns = (
        ("ogc_fid",       PKEY),
        ) + MPGeometry.columns + (
        ("zip", "text"),
        ("street_desc", "text"),
        )
    
    def __init__(self, mp_file, initial_info, *args, **kwargs):
        super(MPPoi, self).__init__(mp_file, initial_info, *args, **kwargs)

    def handle_line(self, line):
        if line.startswith('Data'):
            coords = line.split('=')[1].strip()
            self.record['wkb_geometry'] = xy_from_text(coords)
        elif line.startswith('StreetDesc='):
            self.record['street_desc'] = line.split('=')[1].strip()
        else:
            return super(MPPoi, self).handle_line(line)
        return True

class MPNumbers(MPRecord):
    table_name = "mp_numbers"
    columns = MPRecord.columns + (
        ("id", PKEY),
        ("mp_line_ogc_fid", "int NOT NULL REFERENCES mp_line(ogc_fid)"),
        ("definition_idx", "int NOT NULL"),
        ("point_idx", "int NOT NULL"),
        ("left_side_style", "character varying(1)"),
        ("left_side_start", VARCHAR),
        ("left_side_end", VARCHAR),
        ("right_side_style", "character varying(1)"),
        ("right_side_start", VARCHAR),
        ("right_side_end", VARCHAR),
        ("left_side_zip", VARCHAR),
        ("right_side_zip", VARCHAR),
        ("left_side_city", VARCHAR),
        ("left_side_region", VARCHAR),
        ("left_side_country", VARCHAR),
        ("right_side_city", VARCHAR),
        ("right_side_region", VARCHAR),
        ("right_side_country", VARCHAR),
        )

    varchar_column_names = tuple([r[0] for r in columns[-14:]])

    def __init__(self, line, parent, *args, **kwargs):
        self.record = {}
        self.record['mp_line_ogc_fid'] = parent.pk
        parts = line.split('=')
        self.record['definition_idx'] = int(parts[0].strip("Numbers"))
        number_info = parts[1].strip().split(',')
        self.record['point_idx'] = int(number_info[0])
        for key, res in zip(self.varchar_column_names, number_info[1:]):
            if res != '':
                self.record[key] = res

class MPNode(MPRecord):
    table_name = "mp_node"
    columns = MPRecord.columns + (
        ("id", PKEY),
        ("bound", FLAG_DEF_FALSE),
        )

    def __init__(self, mp_file, initial_info, *args, **kwargs):
        super(MPNode, self).__init__(mp_file, initial_info, *args, **kwargs)        
                
class MPLine(MPGeometry):
    table_name = "mp_line"
    geotype = 'LINESTRING'
    columns = (
        ("ogc_fid",       PKEY),
        ) + MPGeometry.columns + (
        ("zip", "text"),
        ("oneway", FLAG_DEF_FALSE),
        ("toll", FLAG_DEF_FALSE),
        ("dir_indicator", FLAG_DEF_FALSE),
        ("speed", "numeric(2,0)"),
        ("road_class", "numeric(2,0)"),
        ("road_id", VARCHAR),
        ("not_for_emergency", FLAG_DEF_FALSE),
        ("not_for_goods", FLAG_DEF_FALSE),
        ("not_for_car", FLAG_DEF_FALSE),
        ("not_for_bus", FLAG_DEF_FALSE),
        ("not_for_taxi", FLAG_DEF_FALSE),
        ("not_for_foot", FLAG_DEF_FALSE),
        ("not_for_bicycle", FLAG_DEF_FALSE),
        ("not_for_truck", FLAG_DEF_FALSE),
        )
    
    def __init__(self, mp_file, initial_info, primary_key, *args, **kwargs):
        self.numbers = []
        self.nodes = []
        super(MPLine, self).__init__(mp_file, initial_info, *args, **kwargs)
        self.pk = primary_key
        self.record['ogc_fid'] = primary_key

    def handle_line(self, line):
        if line.startswith('RouteParam'):
            rparams = line.split('=')[1].split(',')
            nparams = len(rparams)
            # speedval has speeds in km/h corresponding to RouteParam speed value index
            speedval = [8, 20, 40, 56, 72, 93, 108, 128]
            self.record['speed'] = speedval[int(rparams[0])]
            self.record['road_class'] = int(rparams[1])
            if nparams >= 3:
                if rparams[2].strip() == '1':
                    self.record['oneway'] = True
            if nparams >= 4:
                if rparams[3].strip() == '1':
                    self.record['toll'] = True
            
            # Note: taxi is not an approved access key
            if nparams >= 5:
                vehicles = ['emergency', 'goods', 'car', 'bus', 'taxi', 'foot', 'bicycle', 'truck']
                for veh, res in zip(vehicles, rparams[4:]):
                    if res.strip() == '1':
                        self.record['not_for_' + veh] = True
        elif line.startswith('Data'):
            payload_ary = line.split('=')[1].strip().strip("()").split("),(")
            self.record['wkb_geometry'] = [xy_from_text(node) for node in payload_ary]
        elif line.startswith('Numbers'):
            self.numbers.append(MPNumbers(line, self))
        elif line.startswith('DirIndicator'):
            self.record['dir_indicator'] = (line.split('=')[1].strip() == '1')
        elif line.startswith('Nod'):
            parts = line.strip().split('=')
            node_no = int(parts[0].strip("Nod"))
            point_idx, node_id, bound = parts[1].split(",")
            point_idx = int(point_idx)
            node_id = int(node_id)
            bound = (bound == '1')
            self.nodes.append({'node_no': node_no, 'point_idx': point_idx, 'node_id': node_id, 'bound': bound})
        else:
            return super(MPLine, self).handle_line(line)
        return True

    def generate_segments_and_nodes_sql(self):
        segments = []
        new_nodes = []
        nodes_update_sql = ""
        final_point_idx = len(self.record['wkb_geometry']) - 1
        self.nodes.sort(key=lambda node: node['node_id'])
        
        if len(self.nodes) == 0:
            segments.append(MPSegment(self, None, None, 0, final_point_idx))
        else:
            first_node = self.nodes[0]
            last_node = self.nodes[-1]
            if first_node['point_idx'] > 0:
                segments.append(MPSegment(self, None, first_node['node_id'], 0, first_node['point_idx']))
            if last_node['point_idx'] < final_point_idx:
                segments.append(MPSegment(self, last_node['node_id'], None, last_node['point_idx'], final_point_idx))
            prev = None
            for node in self.nodes:
                if node['node_id'] not in self.mp_file.created_nodes:
                    new_nodes.append(MPNode(self.mp_file, {'id': node['node_id'], 'bound': node['bound']}))
                    self.mp_file.created_nodes.add(node['node_id'])
                elif node['bound']:
                    nodes_update_sql += "UPDATE %s SET bound = TRUE WHERE id = %s;\n" % (MPNode.table_name, node['node_id'])
                if prev is None:
                    continue
                segments.append(MPSegment(self, prev['node_id'], node['node_id'], prev['point_idx'], node['point_idx']))
                prev = node

        return "".join([node.insert_sql() for node in new_nodes]) + "".join([seg.insert_sql() for seg in segments]) + nodes_update_sql
    
    def insert_sql(self):        
        super_insert_sql = super(MPLine, self).insert_sql()
        numbers_sql = "".join([n.insert_sql() for n in self.numbers])
        nodes_sql = self.generate_segments_and_nodes_sql()
        return super_insert_sql + numbers_sql + nodes_sql

class MPSegment(MPGeometry):
    table_name = "mp_segment"
    geotype = 'LINESTRING'
    columns = (
        ("linz2osm_id", PKEY),
        ) + MPGeometry.columns + (
        ("mp_line_ogc_fid", "int NOT NULL references mp_line(ogc_fid)"),
        ("node_id_start", "int references mp_node(id)"),
        ("node_id_end", "int references mp_node(id)"),
        ("point_idx_start", "int NOT NULL"),
        ("point_idx_end", "int NOT NULL"),
        )

    def __init__(self, parent, node_start, node_end, point_start, point_end, *args, **kwargs):
        copied_records = parent.record.copy()
        if 'wkb_geometry' in copied_records:
            geom = copied_records.pop('wkb_geometry')
        copied_records.pop('ogc_fid', None)
        
        super(MPSegment, self).__init__(parent.mp_file, copied_records, *args, **kwargs)
        
        self.parent = parent
        self.record["mp_line_ogc_fid"] = parent.pk
        self.record["node_id_start"] = node_start
        self.record["node_id_end"] = node_end
        self.record["point_idx_start"] = point_start
        self.record["point_idx_end"] = point_end
        self.record["wkb_geometry"] = geom[point_start:point_end+1]
    
class MPPolygon(MPGeometry):
    table_name = "mp_polygon"
    geotype = 'POLYGON'
    columns = (
        ("ogc_fid",       PKEY),
        ) + MPGeometry.columns + ()
    
    def __init__(self, mp_file, initial_info, *args, **kwargs):
        super(MPPolygon, self).__init__(mp_file, initial_info, *args, **kwargs)
        self.rings = []

    def handle_line(self, line):
        if line.startswith('Data'):
            parts = line.strip().split('=')
            data_idx = int(parts[0].strip("Data"))
            payload_ary = parts[1].strip("()").split("),(")
            self.rings.append((data_idx, [xy_from_text(node) for node in payload_ary]))
        else:
            return super(MPPolygon, self).handle_line(line)
        return True

    def set_geometry(self):
        self.rings.sort(key=lambda ring: ring[0])
        self.record['wkb_geometry'] = Polygon(SRID, self.rings)
    
    def insert_sql(self):
        self.set_geometry()
        return super(MPPolygon, self).insert_sql()

class Polygon(object):
    def __init__(self, srid, rings):
        self.srid = srid
        self.rings = rings

    def __str__(self):
        return "ST_GeomFromEWKT('SRID=%d;POLYGON(%s)')" % (self.srid, ",".join([self.format_ring(ring) for ring in self.rings]))

    @classmethod
    def format_ring(cls, ring):
        # We append the first point to close the ring
        return "(" + ",".join(["%s %s" % (x, y) for (x, y) in ring[1] + [ring[1][0]]]) + ")"
    
class MPFile(object):
    ymd_re = re.compile('(?P<year>[0-9]{4})(?P<month>[0-9]{2})(?P<day>[0-9]{2})')
    
    def __init__(self, mpfile, output, errors):
        self.file_mp = mpfile
        self.out = output
        self.err = errors
        
        # debug/stats counters
        self.poi_counter = 0
        self.polyline_counter = 0
        self.polygon_counter = 0
        
        # flags and global variable
        self.parsing_record = False
        self.rNodeToOsmId = {} # map routing node ids to OSM node ids
        self.nodeid = -1
        self.created_nodes = set()

        # temporary records
        self.clear_temp_records()

    def clear_temp_records(self):
        self.roadid = ''
        self.sufi = None
        self.linzid = None
        self.created_date = None
        self.auto_numbered_date = None
        self.found = False
        self.record = None        
        
    def translate(self):
        self.out.write('BEGIN;\n')
        self.write_headers()
        for line in self.file_mp:
            retval = self.handle_line(line)
            if not retval:
                if self.record:
                    self.err.write("-- Did not parse line (in %s)::: %s" % (self.record.table_name, line))
                else:
                    self.err.write("-- Did not parse line::: %s" % line)
        self.out.write('COMMIT;\n')
        self.err.write("-- Points:    %d\n" % self.poi_counter)
        self.err.write("-- Lines:     %d\n" % self.polyline_counter)
        self.err.write("-- Polygons:  %d\n" % self.polygon_counter)
            
    def write_headers(self):
        self.out.write('SET statement_timeout=60000;\n')
        for cls in [MPImgData, MPCountries, MPRegions, MPCities, MPZipCodes, MPPoi, MPLine, MPNumbers, MPPolygon, MPNode, MPRestrict, MPSegment]:
            self.out.write(cls.table_creation_sql())
        self.out.write('SET statement_timeout=0;\n')

    def default_info(self):
        return {
            'linz_sufi': self.sufi,
            'linz_id': self.linzid,
            'created_date': self.created_date,
            'auto_numbered_date': self.auto_numbered_date,
        }

    def start_record(self, record):
        self.parsing_record = True
        self.record = record
        self.nodeid -= 1

    def close_record_with_line(self, line):
        retval = self.record.close_with_line(line)
        if retval:
            self.out.write(self.record.insert_sql())
            self.parsing_record = False
            self.clear_temp_records()
        return retval
        
    def handle_line(self, line):
        # print line
        # Marker for start of sections
        if line.startswith(';'):
            if line.startswith(';sufi'):
                if line.find('=') >= 0:
                    self.sufi = line.split('=')[1].strip()
                    if self.sufi == '0':
                        self.sufi = None
                else:
                    self.sufi = None

            elif line.startswith(';linzid'):
                if line.find('=') >= 0:
                    self.linzid = line.split('=')[1].strip()
                    if self.linzid == '0':
                        self.linzid = None
                else:
                    self.linzid = None
                    
            elif line.startswith(';created='):
                created_date_text = line.split('=')[1].strip()
                day, month, year = created_date_text.split("/")
                if day and month and year:
                    self.created_date = datetime.date(int(year), int(month), int(day))

            elif line.startswith(';Auto-numbered='):
                auto_numbered_date_text = line.split("=")[1].strip()
                mdata = self.ymd_re.match(auto_numbered_date_text)
                if mdata:
                    self.auto_numbered_date = datetime.date(int(mdata.group("year")), int(mdata.group("month")), int(mdata.group("day")))
                
            else:
                return True
            
        elif line.startswith('['):

            if line.startswith('[END'):
                if self.record and self.record.closable_with(line):
                    return self.close_record_with_line(line)
                else:
                    return False

            # FIXME: what if we're still parsing the old record?
            elif line.startswith(('[POI]','[RGN10]','[RGN20]')):
                self.poi_counter += 1
                self.start_record(MPPoi(self, self.default_info()))
            
            elif line.startswith(('[POLYLINE]','[RGN40]')):
                self.polyline_counter += 1
                self.start_record(MPLine(self, self.default_info(), self.polyline_counter))
            
            elif line.startswith(('[POLYGON]','[RGN80]')):
                self.polygon_counter += 1
                self.start_record(MPPolygon(self, self.default_info()))

            elif line.startswith(('[RESTRICT]', '[Restrict]',)):
                self.start_record(MPRestrict(self, self.default_info()))

            elif line.startswith('[IMG ID]'):
                self.start_record(MPImgData(self, {}))
                
            elif line.startswith(('[COUNTRIES]', '[Countries]')):
                self.start_record(MPCountries(self, {}))

            elif line.startswith(('[REGIONS]', '[Regions]')):
                self.start_record(MPRegions(self, {}))
            
            elif line.startswith(('[CITIES]', '[Cities]')):
                self.start_record(MPCities(self, {}))
                
            elif line.startswith(('[ZIPCODES]', '[ZipCodes]')):
                self.start_record(MPZipCodes(self, {}))
                
            else:
                return False
            
        elif self.parsing_record:
            return self.record.handle_line(line)

        elif line.strip() == "":
            pass

        else:
            return False
        
        return True


# Main flow
if len(sys.argv) < 2:
    print "Usage: python mp2postgis.py <file.mp>"
    exit()

# globals
mp_file = MPFile(open(sys.argv[1]), sys.stdout, sys.stderr)
mp_file.translate()
exit()

############################################################
############################################################
############################################################

for line in file_mp:
     
    # parsing data
    if poi or polyline or polygon:
       

        # Get nodes from all zoom levels (ie. Data0, Data1, etc)
        # TODO: Only grab the lowest-numbered data line (highest-resolution) and ignore the rest
        if line.startswith('Data'):
            if polyline or polygon:
                # Just grab the line and parse it later when the [END] element is encountered
                coords = line.split('=')[1].strip() + ','
                # TODO: parse out "holes" in a polygon by reading multiple Data0 lines and
                # constructing a multipolygon relation
        if line.startswith('Nod'):
            if polyline:
                # Store the point index and routing node id for later use
                nod = line.split('=')[1].strip().split(',', 2)
                rnodes[nod[0]] = nod[1]
        if line.startswith('[END]'):
            if polyline or polygon:
                # Have to write out nodes as they are parsed
                nodidx = 0
                nodIds = []
                reused = False
                while coords != '':
                    coords = coords.split(',', 2)
                    if str(nodidx) in rnodes:
                        if rnodes[str(nodidx)] in rNodeToOsmId:
                            curId = rNodeToOsmId[str(rnodes[str(nodidx)])]
                            reused = True
                        else:
                            curId = nodeid
                            nodeid -= 1
                            rNodeToOsmId[str(rnodes[str(nodidx)])] = curId
                    else:
                        curId = nodeid
                        nodeid -= 1
                    nodIds.append(curId)
                    # Don't write another node element if we reused an existing one
                    if not reused:
                        nodes = ET.Element('node', visible='true', version=str(xmlversion), timestamp=str(timestamp), id=str(curId), lat=str(float(coords[0][1:])), lon=str(float(coords[1][:-1])))
                        nodes.text = '\n    '
                        nodes.tail = '\n  '
#                        osm.append(nodes)
                        f.write(ET.tostring(nodes))

                    coords = coords[2]
                    reused = False
                    nodidx += 1
                nodidx = 0
                for ndid in nodIds:
                    nd = ET.Element('nd', ref=str(ndid))
                    nd.tail = '\n    '
                    node.append(nd)
            if polygon:
                nd = ET.Element('nd', ref=str(nodIds[0]))
                nd.tail = '\n    '
                node.append(nd)

