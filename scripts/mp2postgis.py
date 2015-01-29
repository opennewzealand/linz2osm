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

from math import pi, atan2, sin, cos
from textwrap import dedent
from unmangle import interpret_label

SRID = 4326
PKEY = "serial PRIMARY KEY"
VARCHAR = "character varying(255)"
FLAG_DEF_FALSE = "boolean NOT NULL DEFAULT FALSE"

SEGMENT_TYPE_MAP = {
     # TODO FIXME all these highway types, and links need to be checked
     # These are not necessarily OSM types
     0x1: ('highway', 'motorway'),   # added by JR
     0x2: ('highway', 'trunk'),
     0x3: ('highway', 'primary'),
     0x4: ('highway', 'secondary'),
     0x5: ('highway', 'tertiary'),
     0x6: ('highway', 'residential'),
     0x7: ('highway', 'service'), # added by JR - TODO confirm in other places, example is Auckland airport's Cyril Kay Rd.. cf 0x7 as polygon which is diff.
     0x8: ('highway', 'primary_link'), # added by JR - TODO FIXME what is a turning point (U-Turn etc) on a big road? this is actually on a tertiary road when i looked
     0x9: ('highway', 'secondary_link'), # added by JR - TODO FIXME in the LINZ dataset is this actually used to connect secondary roads, or other types?
     0xa: ('highway', 'track_unpaved'),
     0xb: ('highway', 'trunk_link'), # added by JR
     0xc: ('highway', 'roundabout'), # added by JR - was junction: roundabout
     0xd: ('highway', 'cycleway'), # added by JR

     0x14: ('railway', 'rail'), # added by JR
     0x16: ('highway', 'footway'), # added by JR
     0x18: ('waterway', 'stream'),
     0x19: ('timezone', 'timezone_boundary'),
     0x1a: ('route', 'ferry'),
     0x1b: ('route', 'ferry'), # added by JR

     # boundaries http://wiki.openstreetmap.org/wiki/Key:admin_level#10_admin_level_values_for_specific_countries
     0x1c: ('boundary', 'region'), # added by JR, seems to be e.g. Otago/Canterbury, Auckland/Waikato TODO check this
     0x1d: ('boundary', 'district'), # added by JR, seems to be e.g. Timaru district council, TODO check this

     0x1f: ('waterway', 'canal'), # added by JR, was 'river', but the only ones present are in Chch canals
     0x29: ('power', 'line'),
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

def _deg2rad(deg):
    return deg * (pi / 180.0)

def _rad2deg(rad):
    return rad * (180.0 / pi)

# The Earth is a sphere, donchaknow.
# From http://www.ig.utexas.edu/outreach/googleearth/latlong.html
def bearing(point_a, point_b):
    ax, ay = point_a
    bx, by = point_b

    # Everyone loves their lat/longs in radians instead of degrees
    axr, ayr = _deg2rad(float(ax)), _deg2rad(float(ay))
    bxr, byr = _deg2rad(float(bx)), _deg2rad(float(by))

    bearing_rads = atan2(
        sin(bxr - axr) * cos(byr),
        cos(ayr) * sin(byr) - sin(ayr) * cos(byr) * cos(bxr - axr)
    )

    return _rad2deg(bearing_rads)

def normalise_bearing(bearing_degrees):
    return (180.0 + bearing_degrees) % 360.0 - 180.0

def reverse_bearing(bearing_degrees):
    return normalise_bearing(bearing_degrees + 180)

def relative_bearing(a, b):
    return normalise_bearing(b - a)

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
    def post_processing_sql(cls, mp_file):
        return ""

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
    _last_mp_restrict_id = 0
    table_name = "mp_restrict"
    closing_tags = MPRecord.closing_tags + ("[END-RESTRICT]", "[END-Restrict]",)
    columns = MPRecord.columns + (
        ("id", PKEY),
        ("nod", "integer"),
        ("node_id_1", "integer"), # REFERENCES mp_node(id)
        ("node_id_2", "integer"), # REFERENCES mp_node(id)
        ("node_id_3", "integer"), # REFERENCES mp_node(id)
        ("node_id_4", "integer"), # REFERENCES mp_node(id)
        ("road_id_1", VARCHAR),
        ("road_id_2", VARCHAR),
        ("road_id_3", VARCHAR),
        ("not_for_emergency", FLAG_DEF_FALSE),
        ("not_for_goods", FLAG_DEF_FALSE),
        ("not_for_car", FLAG_DEF_FALSE),
        ("not_for_bus", FLAG_DEF_FALSE),
        ("not_for_taxi", FLAG_DEF_FALSE),
        ("not_for_foot", FLAG_DEF_FALSE),
        ("not_for_bicycle", FLAG_DEF_FALSE),
        ("not_for_truck", FLAG_DEF_FALSE),
        ("turn_angle", "double precision"),
        ("turn_type", VARCHAR),
        )

    def __init__(self, mp_file, initial_info, *args, **kwargs):
        super(MPRestrict, self).__init__(mp_file, initial_info, *args, **kwargs)
        self.record["id"] = self._next_id()

    @classmethod
    def _next_id(cls):
        cls._last_mp_restrict_id += 1
        return cls._last_mp_restrict_id

    def handle_line(self, line):
        if line.startswith("TraffPoints"):
            traff_points = line.split("=")[1].strip().split(",")[:4]
            for (counter, traff_point) in enumerate(traff_points):
                self.record["node_id_%d" % (counter + 1,)] = int(traff_point)
        elif line.startswith("TraffRoads"):
            traff_roads = line.split("=")[1].strip().split(",")[:3]
            for (counter, traff_road) in enumerate(traff_roads):
                self.record["road_id_%d" % (counter + 1,)] = str(traff_road)
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

    def close_with_line(self, line):
        self.mp_file.restrictions_db.append(self)
        return super(MPRestrict, self).close_with_line(line)

    @classmethod
    def post_processing_sql(cls, mp_file):
        return cls.bearings_sql(mp_file)

    @classmethod
    def bearings_sql(cls, mp_file):
        output_sql = []
        seg_db = mp_file.segments_db
        segs_for_node = dict([(node_id, []) for node_id in mp_file.created_nodes])
        for segment in seg_db:
            try:
                for record_part in ["node_id_start", "node_id_end"]:
                    if segment.record[record_part]:
                        segs_for_node[segment.record[record_part]].append(segment)
            except KeyError:
                mp_file.err.write(repr(segs_for_node.keys()))
                mp_file.err.write("\n=====================================================\n")
                mp_file.err.write(repr(segment.record))
                raise

        for r in mp_file.restrictions_db:
            # mp_file.err.write("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n")
            segments_at_node = segs_for_node[r.record["nod"]]
            from_segment = None
            to_segment = None
            bearing_into = None         # The bearing INTO the node from source
            bearing_out = None          # The bearing OUT of the node into destination. Adjusted to be relative to bearing_into.
            bearing_source = None       # The bearing OUT of the node into the source of the continuing road. Adjusted to be relative to bearing_into.
            bearing_continuation = None # The bearing OUT of the node into the destination of the continuing road. Adjusted to be relative to bearing_into.
            restriction_on_same_road = (r.record["road_id_1"] == r.record["road_id_2"])
            u_turn = (restriction_on_same_road and (r.record["node_id_1"] == r.record["node_id_3"]))
            continuation_of_from_road = None
            source_of_to_road = None
            other_segments = []
            turn_type = "turn";

            if not segments_at_node:
                raise ValueError("No segments matching restriction")

            # mp_file.err.write("restriction %s: %s (road=%s) -> %s -> %s (road=%s))\n" % (
            #     r.record.get("id"), r.record["node_id_1"], r.record["road_id_1"], r.record["nod"], r.record["node_id_3"], r.record["road_id_2"]
            # ))

            # Get the important segments
            for seg in segments_at_node:
                # mp_file.err.write("segment %s (road=%s), from=%s to=%s bearing_from_start=%f bearing_from_end=%f\n" % (
                #     seg.record.get("linz2osm_id"), seg.record["road_id"], seg.record["node_id_start"], seg.record["node_id_end"], seg.record["bearing_from_start_node"], seg.record["bearing_from_end_node"]
                # ))
                # Get the bearing from the correct node
                if seg.record["node_id_start"] == r.record["nod"]:
                    seg_bearing = seg.record["bearing_from_start_node"]
                elif seg.record["node_id_end"] == r.record["nod"]:
                    seg_bearing = seg.record["bearing_from_end_node"]
                else:
                    raise ValueError("Should not happen: segment does not match node at either end")

                # This is the same road as the source. Is it the source?
                if seg.record["road_id"] == r.record["road_id_1"]:
                    if (seg.record["node_id_start"] == r.record["node_id_1"]):
                        from_segment = seg
                        bearing_into = reverse_bearing(seg_bearing)
                    elif (seg.record["node_id_end"] == r.record["node_id_1"]):
                        from_segment = seg
                        bearing_into = reverse_bearing(seg_bearing)
                    elif u_turn or not restriction_on_same_road:
                        continuation_of_from_road = seg
                        bearing_continuation = normalise_bearing(seg_bearing)

                # This is the same road as the destination. Is it the destination?
                if seg.record["road_id"] == r.record["road_id_2"]:
                    if (seg.record["node_id_start"] == r.record["node_id_3"]):
                        to_segment = seg
                        bearing_out = normalise_bearing(seg_bearing)
                    elif (seg.record["node_id_end"] == r.record["node_id_3"]):
                        to_segment = seg
                        bearing_out = normalise_bearing(seg_bearing)
                    elif u_turn or not restriction_on_same_road:
                        source_of_to_road = seg
                        bearing_source = normalise_bearing(seg_bearing)

                # This is not the same road as source or destination?
                if seg.record["road_id"] not in (r.record["road_id_1"], r.record["road_id_2"]):
                    other_segments.append(seg_bearing)

            if bearing_into is not None and bearing_out is not None and from_segment is not None and to_segment is not None:
                # Includes the continuation and source, as well.
                all_other_segments = list(other_segments)
                # Adjust bearings to be relative
                bearing_out = relative_bearing(bearing_into, bearing_out)
                if bearing_continuation:
                    bearing_continuation = relative_bearing(bearing_into, bearing_continuation)
                    all_other_segments.append(bearing_continuation)
                if bearing_source:
                    bearing_source = relative_bearing(bearing_into, bearing_source)
                    all_other_segments.append(bearing_source)

                bearing_out_is_closest_to_straight = all([abs(a) > bearing_out for a in all_other_segments])
                # mp_file.err.write("Bearing out is closest to straight=%s\n" % bearing_out_is_closest_to_straight)

                sorted_all_other_segments = sorted([relative_bearing(bearing_into, b) for b in all_other_segments])
                sorted_other_segments = sorted([relative_bearing(bearing_into, b) for b in other_segments])

                segments_left_of_destination = len([s for s in sorted_all_other_segments if s < bearing_out])
                segments_right_of_destination = len([s for s in sorted_all_other_segments if s > bearing_out])

                segments_left_of_continuation = len([s for s in sorted_other_segments if s < bearing_continuation])
                segments_right_of_continuation = len([s for s in sorted_other_segments if s > bearing_continuation])

                segments_left_of_source = len([s for s in sorted_other_segments if s < bearing_source])
                segments_right_of_source = len([s for s in sorted_other_segments if s > bearing_source])

                # mp_file.err.write("For restriction %s, in=%f out=%f src=%s cont=%s num_other_segments=%d (%s)\n" % (
                #     r.record.get("id"), bearing_into, bearing_out,
                #     str(bearing_source), str(bearing_continuation),
                #     len(sorted_other_segments), ', '.join([str(a) for a in sorted_other_segments])
                # ))
                # mp_file.err.write("Of destination L=%d, R=%d, of continuation L=%d, R=%d, of source L=%d, R=%d\n" % (
                #     segments_left_of_destination, segments_right_of_destination,
                #     segments_left_of_continuation, segments_right_of_continuation,
                #     segments_left_of_source, segments_right_of_source,
                # ))

                if u_turn:
                    turn_type = "u_turn"
                elif not all_other_segments:
                    turn_type = "straight_on"
                elif not continuation_of_from_road and not source_of_to_road:
                    if segments_left_of_destination == 0:
                        turn_type = "left_turn"
                    elif segments_right_of_destination == 0:
                        turn_type = "right_turn"
                elif restriction_on_same_road:
                    if segments_left_of_destination == 0 and bearing_out < 0.0:
                        turn_type = "left_turn"
                    elif segments_right_of_destination == 0 and bearing_out > 0.0:
                        turn_type = "right_turn"
                    else:
                        turn_type = "straight_on"
                elif continuation_of_from_road:
                    if bearing_out < bearing_continuation:
                        turn_type = "left_turn"
                    elif bearing_out > bearing_continuation:
                        turn_type = "right_turn"
                elif source_of_to_road:
                    if bearing_out < bearing_source:
                        turn_type = "left_turn"
                    elif bearing_out > bearing_source:
                        turn_type = "right_turn"

                if turn_type == "turn":
                    if bearing_out_is_closest_to_straight:
                        turn_type = "straight_on"
                    elif bearing_out < 0:
                        turn_type = "left_turn"
                    elif bearing_out > 0:
                        turn_type = "right_turn"
                    else:
                        turn_type = "straight_on"

                # mp_file.err.write("Resulting turn is: %s\n" % turn_type)
                output_sql.append("""
                    UPDATE %s SET (turn_type, turn_angle) = ('%s', %f) WHERE id = %d;
                """ % (
                    cls.table_name, turn_type, bearing_out, r.record["id"]
                ))
            else:
                mp_file.err.write("Could not calculate angle for MPRestrict %s\n" % str(r.record))

        return "\n".join(output_sql)



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
            DROP TABLE IF EXISTS %(table_name)s CASCADE;
            CREATE TABLE %(table_name)s (%(columns_sql)s);
            SELECT AddGeometryColumn('%(table_name)s'::varchar, 'wkb_geometry'::varchar, %(srid)d, '%(geotype)s'::varchar, 2);
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
    geotype = "POINT"
    columns = MPRecord.columns + (
        ("id", PKEY),
        ("bound", FLAG_DEF_FALSE),
        ("wkb_geometry",  "geometry"),
        )

    def __init__(self, mp_file, initial_info, *args, **kwargs):
        super(MPNode, self).__init__(mp_file, initial_info, *args, **kwargs)

    @classmethod
    def table_creation_sql(cls):
        return super(MPNode, cls).table_creation_sql() + dedent("""
            SELECT AddGeometryColumn('%(table_name)s'::varchar, 'wkb_geometry'::varchar, %(srid)d, '%(geotype)s'::varchar, 2);
        """) % {
            'table_name': cls.table_name,
            'srid': SRID,
            'geotype': cls.geotype,
        }

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
        ("speed", "numeric(5,0)"),
        ("road_class", "numeric(5,0)"),
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
        self.nodes.sort(key=lambda node: node['point_idx'])

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
                    new_nodes.append(MPNode(self.mp_file, {
                        'id': node['node_id'],
                        'bound': node['bound'],
                        'wkb_geometry': self.record['wkb_geometry'][node['point_idx']]
                    }))
                    self.mp_file.created_nodes.add(node['node_id'])
                elif node['bound']:
                    nodes_update_sql += "UPDATE %s SET bound = TRUE WHERE id = %s;\n" % (MPNode.table_name, node['node_id'])
                if prev is None:
                    prev = node
                    continue
                segments.append(MPSegment(self, prev['node_id'], node['node_id'], prev['point_idx'], node['point_idx']))
                prev = node

        self.mp_file.segments_db.extend(segments)
        return dedent("".join([node.insert_sql() for node in new_nodes]) +
                      "".join([seg.insert_sql() for seg in segments]) +
                      nodes_update_sql)

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
        ("subtype", VARCHAR),
        ) + MPGeometry.columns + (
        ("mp_line_ogc_fid", "int NOT NULL references mp_line(ogc_fid)"),
        ("node_id_start", "int references mp_node(id)"),
        ("node_id_end", "int references mp_node(id)"),
        # Both of these bearings are AWAY from the node in question.
        ("bearing_from_start_node", "double precision"),
        ("bearing_from_end_node", "double precision"),
        ("point_idx_start", "int NOT NULL"),
        ("point_idx_end", "int NOT NULL"),

        # MPLine columns
        ("zip", "text"),
        ("oneway", FLAG_DEF_FALSE),
        ("toll", FLAG_DEF_FALSE),
        ("dir_indicator", FLAG_DEF_FALSE),
        ("speed", "numeric(5,0)"),
        ("road_class", "numeric(5,0)"),
        ("road_id", VARCHAR),
        ("not_for_emergency", FLAG_DEF_FALSE),
        ("not_for_goods", FLAG_DEF_FALSE),
        ("not_for_car", FLAG_DEF_FALSE),
        ("not_for_bus", FLAG_DEF_FALSE),
        ("not_for_taxi", FLAG_DEF_FALSE),
        ("not_for_foot", FLAG_DEF_FALSE),
        ("not_for_bicycle", FLAG_DEF_FALSE),
        ("not_for_truck", FLAG_DEF_FALSE),
        ("label_unmangled", "text"),
        ("exit_ref", "text"),
        ("exit_name", "text"),
        ("calculated_subtype", "text"),
        )

    LINK_RE = re.compile(r"^(?P<prefix>.*)_link$")

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

        seg_geom = geom[point_start:point_end+1]
        self.record["wkb_geometry"] = seg_geom
        self.record["bearing_from_start_node"] = bearing(seg_geom[0], seg_geom[1])
        self.record["bearing_from_end_node"] = bearing(seg_geom[-1], seg_geom[-2])

        self.record["subtype"] = SEGMENT_TYPE_MAP.get(self.record["type"])[1]

        ip = interpret_label(self.record.get("label"))
        self.record["label_unmangled"] = ip.get('label')
        self.record["exit_ref"] = ip.get('exit_ref')
        self.record["exit_name"] = ip.get('exit_name')

        self.record["calculated_subtype"] = self.record["subtype"]

    def is_link(self):
        return bool(self.LINK_RE.search(self.record["subtype"]))

    def __str__(self):
        return "Segment %d/%d : %d -> %d" % (self.record["mp_line_ogc_fid"], self.record["point_idx_start"], self.record["node_id_start"], self.record["node_id_end"])

    @classmethod
    def table_creation_sql(cls):
        return super(MPSegment, cls).table_creation_sql() + "".join([
                dedent("""
                    CREATE TABLE %(table_name)s_%(type_name)s (LIKE %(table_name)s);
                    INSERT INTO geometry_columns (
                        f_table_catalog,
                        f_table_schema,
                        f_table_name,
                        f_geometry_column,
                        coord_dimension,
                        srid,
                        type
                    ) VALUES (
                        '',
                        'public',
                        '%(table_name)s_%(type_name)s',
                        'wkb_geometry',
                        2,
                        4326,
                        'LINESTRING'
                    );
                    """) % {
                    'table_name': cls.table_name,
                    'type_name': type_name,
                    } for type_name in list(set([tm[0] for tm in SEGMENT_TYPE_MAP.values()]))])

    @classmethod
    def post_processing_sql(cls, mp_file):
        return cls.segments_link_types_sql(mp_file) + cls.segments_type_specific_tables_sql(mp_file)

    @classmethod
    def segments_type_specific_tables_sql(cls, mp_file):
        return "".join([dedent("""
            INSERT INTO %(table_name)s_%(type_name)s SELECT * FROM %(table_name)s WHERE type = %(type_code)d;
        """ % {
                    'table_name': cls.table_name,
                    'type_name': tm[0],
                    'type_code': type_code,
                    }) for type_code, tm in SEGMENT_TYPE_MAP.iteritems()])

    @classmethod
    def segments_link_types_sql(cls, mp_file):
        seg_db = mp_file.segments_db
        segs_for_node = dict([(node_id, []) for node_id in mp_file.created_nodes])
        for segment in seg_db:
            try:
                for record_part in ["node_id_start", "node_id_end"]:
                    if segment.record[record_part]:
                        segs_for_node[segment.record[record_part]].append(segment)
            except KeyError:
                mp_file.err.write(repr(segs_for_node.keys()))
                mp_file.err.write("\n=====================================================\n")
                mp_file.err.write(repr(segment.record))
                raise



        links = [seg for seg in seg_db if seg.is_link()]
        mp_file.err.write("There are %d nodes and %d segments of which %d are links\n" % (len(segs_for_node), len(seg_db), len(links)))
        while True:
            any_mods = False
            for segment in links:
                new_type = cls.upgraded_type(segs_for_node, segment)
                if new_type != segment.record["calculated_subtype"]:
                    mp_file.err.write("-- Changing %s from %s to %s (originally %s)\n" % (segment.record["label_unmangled"], segment.record["calculated_subtype"], new_type, segment.record["subtype"]))
                    segment.record["calculated_subtype"] = new_type
                    any_mods = True
            if not any_mods:
                break

        output_sql = []

        for segment in seg_db:
            if segment.record["calculated_subtype"] != segment.record["subtype"]:
                output_sql.append("UPDATE %s SET calculated_subtype = '%s' WHERE mp_line_ogc_fid = %d AND point_idx_start = %d;" % (cls.table_name, segment.record["calculated_subtype"], segment.record["mp_line_ogc_fid"], segment.record["point_idx_start"]))
        return "\n".join(output_sql)

    @classmethod
    def upgraded_type(cls, segs_for_node, seg):
        best_at_start = cls.best_type_at_node(segs_for_node, seg, seg.record["node_id_start"])
        best_at_end = cls.best_type_at_node(segs_for_node, seg, seg.record["node_id_end"])
        return cls.higher_type(best_at_start, best_at_end) + "_link"

    TYPES_HEIRARCHY = [
        "motorway",
        "trunk",
        "primary",
        "secondary",
        "tertiary",
        "motorway_link",
        "trunk_link",
        "primary_link",
        "secondary_link",
        "tertiary_link",
        ]

    @classmethod
    def higher_type(cls, type_a, type_b):
        if cls.TYPES_HEIRARCHY.index(type_a) < cls.TYPES_HEIRARCHY.index(type_b):
            return type_a
        else:
            return type_b

    @classmethod
    def best_type_at_node(cls, segs_for_node, seg, node_id):
        seg_types_at_this_node = [s.record["calculated_subtype"] for s in segs_for_node[node_id] if s != seg]
        current_best = "tertiary_link"
        for st in seg_types_at_this_node:
            if st in cls.TYPES_HEIRARCHY:
                current_best = cls.higher_type(st, current_best)
            else:
                current_best = cls.higher_type("tertiary", current_best)

        return current_best.replace("_link", "")

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

TABLE_CLASSES = [MPImgData, MPCountries, MPRegions, MPCities, MPZipCodes, MPPoi, MPLine, MPNumbers, MPPolygon, MPNode, MPRestrict, MPSegment]

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
        self.created_nodes = set()
        self.segments_db = []
        self.restrictions_db = []

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
        self.out.write('COMMIT;\n')
        self.out.write('BEGIN;\n')
        for line in self.file_mp:
            retval = self.handle_line(line)
            if not retval:
                if self.record:
                    self.err.write("-- Did not parse line (in %s)::: %s" % (self.record.table_name, line))
                else:
                    self.err.write("-- Did not parse line::: %s" % line)
        self.out.write('COMMIT;\n')
        self.out.write('BEGIN;\n')
        for cls in TABLE_CLASSES:
            self.out.write(cls.post_processing_sql(mp_file))
        self.out.write('COMMIT;\n')
        self.err.write("-- Points:    %d\n" % self.poi_counter)
        self.err.write("-- Lines:     %d\n" % self.polyline_counter)
        self.err.write("-- Polygons:  %d\n" % self.polygon_counter)

    def write_headers(self):
        self.out.write('SET statement_timeout=60000;\n')
        for cls in TABLE_CLASSES:
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
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: python mp2postgis.py <file.mp>"
        exit()

    # globals
    mp_file = MPFile(open(sys.argv[1]), sys.stdout, sys.stderr)
    mp_file.translate()
    exit()

