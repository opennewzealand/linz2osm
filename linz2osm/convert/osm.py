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

import hashlib
import json
import math
import re

from cStringIO import StringIO
from textwrap import dedent
from xml.etree import ElementTree

from django.conf import settings
from django.contrib.gis import geos
from django.core.cache import cache
from django.db import connection, connections

from linz2osm.convert import overpass


def get_srtext_from_srid(srid):
    cursor = connection.cursor()
    cursor.execute('SELECT srtext FROM spatial_ref_sys WHERE srid=%s;', [srid])
    return cursor.fetchone()[0]

def get_layer_geometry_type(database_id, layer):
    """ Returns a (geometry_type, srid) tuple """
    if layer.geometry_type == 'RELATION':
        geotypes = get_relation_geometry_types(database_id, layer)
        if not geotypes:
            raise ValueError("No members for relation")
        srid = geotypes.values()[0][1]
        if not all([srid == s for (geotype, s) in geotypes.values()]):
            raise ValueError("SRIDs differ for relation layers!")
        return ("GEOMETRYCOLLECTION", srid)
    else:
        cursor = connections[database_id].cursor()
        cursor.execute('SELECT type, srid FROM geometry_columns WHERE f_table_name=%s;', [layer.name])
        r = cursor.fetchone()
        if not r:
            raise ValueError("Could not get geometry_columns information for %s.%s" % (database_id, layer.name))
        return tuple(r[:2])

def get_relation_geometry_types(database_id, layer):
    r = {}
    for member in layer.members.select_related('member_layer').all():
        r[member.member_layer.name] = get_layer_geometry_type(database_id, member.member_layer)
    return r


def get_base_and_limit_feature_ids(layer_in_dataset, base_id=None, feature_limit=None):
    cursor = connections[layer_in_dataset.dataset.name].cursor()

    sql = 'SELECT %(layer_name)s.%(pkey_name)s FROM %(layer_name)s '
    params = {
        'pkey_name': layer_in_dataset.layer.pkey_name,
        'layer_name': layer_in_dataset.layer.name,
        'base_id': int(base_id),
        'feature_limit': int(feature_limit),
        }

    if base_id:
        sql += ' WHERE %(layer_name)s.%(pkey_name)s >= %(base_id)d'

    sql += ' ORDER BY %(layer_name)s.%(pkey_name)s ASC'

    if feature_limit:
        sql += ' LIMIT %(feature_limit)d'

    cursor.execute(sql % params)
    return [r[0] for r in cursor.fetchall()]

def get_layer_feature_ids(layer_in_dataset, extent=None, feature_limit=None):
    cursor = connections[layer_in_dataset.dataset.name].cursor()

    sql = 'SELECT %(layer_name)s.%(pkey_name)s FROM %(layer_name)s '
    sql += layer_in_dataset.layer.join_sql
    params = []

    if extent:
        srid = layer_in_dataset.dataset.srid
        extent_trans = extent.hexewkb
        sql += ' WHERE ST_CoveredBy(ST_Centroid(%(geometry_expression)s), ST_Transform(%%s::geometry, %%s)) OR ST_CoveredBy(ST_Centroid(%(geometry_expression)s), ST_Transform(ST_Translate(%%s::geometry, 360.0, 0.0), %%s))'
        params += [extent_trans, srid, extent_trans, srid]

    sql += ' ORDER BY %(layer_name)s.%(pkey_name)s'
    if feature_limit:
        sql += ' LIMIT %d' % (feature_limit + 1)

    print sql

    cursor.execute(sql % {
        'pkey_name': layer_in_dataset.layer.pkey_name,
        'layer_name': layer_in_dataset.layer.name,
        'geometry_expression': layer_in_dataset.layer.geometry_expression
    }, params)

    if (feature_limit is not None) and cursor.rowcount > feature_limit:
        return None # FIXME: use exceptions - should have checked feature count before approving workslice
    return [r[0] for r in cursor.fetchall()]

def feature_selection_geojson(workslice_features, centroids_only=False):
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
            """ % ",".join(filter(None, [wf.wgs_geojson(centroids_only) for wf in workslice_features])))

def get_layer_feature_count(database_id, layer, intersect_geom=None):
    cursor = connections[database_id].cursor()
    layer_srid = get_layer_geometry_type(database_id, layer)[1]
    if intersect_geom and intersect_geom.srid is None:
        intersect_geom.srid = layer_srid

    sql = 'SELECT count(*) FROM %(layer_name)s '
    sql += layer.join_sql
    params = []
    if intersect_geom:
        intersect_trans = intersect_geom.hexewkb
        sql += ' WHERE ST_CoveredBy(ST_Centroid(%(geometry_expression)s), ST_Transform(%%s::geometry, %%s)) OR ST_CoveredBy(ST_Centroid(%(geometry_expression)s), ST_Transform(ST_Translate(%%s::geometry, 360.0, 0.0), %%s))'
        params += [intersect_trans, layer_srid, intersect_trans, layer_srid]

    cursor.execute(sql % {
        'layer_name': layer.name,
        'geometry_expression': layer.geometry_expression
    },
    params)
    return cursor.fetchone()[0]

class NoSuchFieldNameError(Exception):
    pass

NO_STATS_FIELDS = ['wkb_geometry']

def get_field_stats(database_id, layer, field_name):
    geom_type, srid = get_layer_geometry_type(database_id, layer)
    cursor = connections[database_id].cursor()
    if not re.match("\w+", field_name):
        raise NoSuchFieldNameError
    if field_name in NO_STATS_FIELDS or field_name == layer.pkey_name:
        raise NoSuchFieldNameError
    cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_name=%s AND column_name=%s;", [layer.name, field_name])
    col_type_row = cursor.fetchone()
    if col_type_row is None:
        raise NoSuchFieldNameError
    col_type = col_type_row[0]

    sql = "SELECT \"%(c)s\", count(*) FROM \"%(t)s\" WHERE \"%(c)s\" IS NOT NULL "
    if col_type in ('character varying',):
        sql += " AND \"%(c)s\" <> '' "
    sql += "GROUP BY \"%(c)s\" ORDER BY count(*) DESC, \"%(c)s\" ASC; "

    cursor.execute(sql % {'t': layer.name, 'c': field_name})
    return cursor.fetchall()

def get_layer_stats(database_id, layer):
    # FIXME: use layer_in_dataset object
    geom_type, srid = get_layer_geometry_type(database_id, layer)
    cursor = connections[database_id].cursor()

    # Expand bounds by 1,001 metres (or, if using WGS84, by 0.01 degree)
    if str(srid) in ['4326', '4167']:
        expansion = "0.01"
    else:
        expansion = "1001.0"
    sql = "SELECT ST_AsHexEWKB(ST_Transform(ST_SetSRID(ST_Envelope(ST_Buffer(ST_Extent(%s), %s)), %d), 4326)) FROM %s %s;" % (layer.geometry_expression, expansion, srid, layer.name, layer.join_sql)
    cursor.execute(sql)
    hexwkb = cursor.fetchone()[0]
    if not hexwkb:
        print "%s - %s" % (database_id, layer.name)
        print sql
        raise ValueError("No geometry from SQL: %s" % sql)
    extent = geos.GEOSGeometry(hexwkb)
    et = extent.extent

    r = {
        'feature_count': get_layer_feature_count(database_id, layer),
        'extent': extent,
        'extent_link': "http://www.openstreetmap.org/index.html?minlon=%f&minlat=%f&maxlon=%f&maxlat=%f&box=yes" % et,
        'primary_key': layer.pkey_name,
        'fields': {}
    }

    cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s AND column_name NOT IN (%s, 'wkb_geometry', 'macronated', 'grp_macron', 'mp_line_ogc_fid');", [layer.name, layer.pkey_name])
    for col_name,col_type in cursor.fetchall():
        sql = 'SELECT count(*) FROM "%(t)s" WHERE "%(c)s" IS NOT NULL'
        if col_type in ('character varying',):
            sql += " AND \"%(c)s\" <> ''"
        cursor.execute(sql % {'t': layer.name, 'c': col_name})
        row = cursor.fetchone()
        r['fields'][col_name] = {
            'non_empty_cnt': row[0],
            'non_empty_pc' : row[0] / float(r['feature_count']) * 100.0,
            'col_type': col_type,
            'show_distinct_values': (row[0] > 0 and (col_name not in ('id', 'linz2osm_id', 'ogc_fid', 'name', 'name_id', 'road_name_id', 'elevation') or r['feature_count'] <= 1000)),
        }

    if not layer.geometry_type == 'RELATION':
        if geom_type in ('LINESTRING', 'POLYGON'):
            cursor.execute("SELECT avg(ST_NPoints(wkb_geometry)), max(ST_NPoints(wkb_geometry)) FROM \"%s\";" % layer.name)
            s = cursor.fetchone();
            r.update({
                'points_avg': s[0],
                'points_max': s[1],
            })

        if geom_type == 'POLYGON':
            cursor.execute("SELECT avg(ST_NRings(wkb_geometry)), max(ST_NRings(wkb_geometry)), avg(ST_NPoints(ST_ExteriorRing(wkb_geometry))), max(ST_NPoints(ST_ExteriorRing(wkb_geometry))) FROM \"%s\";" % layer.name)
            s = cursor.fetchone();
            r.update({
                'rings_avg': s[0],
                'rings_max': s[1],
                'points_ext_ring_avg': s[2],
                'points_ext_ring_max': s[3],
            })

    return r


def clean_data(cell):
    if isinstance(cell, unicode) or isinstance(cell, str):
        return cell.strip()
    else:
        return cell

def featureset_conflicts(layer_in_dataset, workslice_features):
    data_table = get_data_table(layer_in_dataset, [wf.feature_id for wf in workslice_features])
    return overpass.featureset_conflicts_for_data(layer_in_dataset, workslice_features, data_table)

def featureset_matches(layer_in_dataset, workslice_features):
    data_table = get_data_table(layer_in_dataset, [wf.feature_id for wf in workslice_features])
    return overpass.featureset_matches_for_data(layer_in_dataset, workslice_features, data_table)

def apply_changeset_to_dataset(dataset_update, table_name, lid):
    database_id = dataset_update.dataset.name
    destination_table = lid.layer.name

    print "Applying changes from %s to %s in %s" % (table_name, lid.layer.name, database_id)

    cursor = connections[database_id].cursor()
    data_columns, geom_column = get_data_columns(cursor, table_name)

    if not geom_column:
        raise NotImplementedError("We don't yet support changeset application to non-geometry tables")

    cursor.execute('SELECT ST_AsEWKB(%s), \"%s\" FROM %s ORDER BY %s' % (geom_column, '\",\"'.join(data_columns), table_name, lid.layer.pkey_name))

    update_table = []
    insert_table = []
    delete_table = []

    for i,row in enumerate(cursor):
        if row[0] is None:
            continue
        row_geom = geos.GEOSGeometry(row[0])
        if row_geom.empty:
            continue

        row_data = dict(zip(data_columns,[clean_data(c) for c in row[1:] ]))
        # print "We have a %s for %d" % (row_data['__change__'], row_data[lid.layer.pkey_name])
        row_data[geom_column] = row_geom

        action = row_data.pop('__change__')

        if action == "UPDATE":
            update_table.append(row_data)
        elif action == "INSERT":
            insert_table.append(row_data)
        elif action == "DELETE":
            delete_table.append(row_data)

    print "%d updates, %d inserts, %d deletes" % (len(update_table), len(insert_table), len(delete_table))

    data_columns.remove('__change__')

    for row in insert_table:
        cursor.execute(
            'INSERT INTO %s (\"%s\", \"%s\") VALUES (\'%s\', %s);' % (
                destination_table,
                geom_column,
                '\",\"'.join(data_columns),
                row[geom_column].hexewkb,
                ', '.join(['%s' for dn in data_columns]),
                ),
            [row[cname] for cname in data_columns])

    for row in update_table:
        cursor.execute(
            'UPDATE %s SET ("%s", "%s") = (\'%s\', %s) WHERE %s = %s;' % (
                destination_table,
                geom_column,
                '\",\"'.join(data_columns),
                row[geom_column].hexewkb,
                ', '.join(['%s' for dn in data_columns]),
                lid.layer.pkey_name,
                row[lid.layer.pkey_name],
                ),
            [row[cname] for cname in data_columns])
        lid.workslicefeature_set.filter(feature_id=row[lid.layer.pkey_name]).update(dirty=2)

    for row in delete_table:
        cursor.execute(
            'DELETE FROM %s WHERE %s = %%s' % (
                destination_table,
                lid.layer.pkey_name
                ),
            (row[lid.layer.pkey_name],))
        lid.workslicefeature_set.filter(feature_id=row[lid.layer.pkey_name]).update(dirty=1)

        # TODO: Create deletion workslice

    stats = get_layer_stats(lid.dataset.name, lid.layer)
    lid.features_total = stats['feature_count']
    lid.extent = lid.extent.union(stats['extent']).envelope
    lid.last_deletions_dump_filename = ''

    lid.save()


def export(workslice):
    layer_in_dataset = workslice.layer_in_dataset
    feature_ids = [wf.feature_id for wf in workslice.workslicefeature_set.all()]
    return export_custom(layer_in_dataset, feature_ids, workslice.id)

def get_data_columns(cursor, layer_name):
    cursor.execute('SELECT column_name, udt_name FROM information_schema.columns WHERE table_name=%s;', [layer_name])
    data_columns = []
    geom_column = None
    for column_name,udt_name in cursor:
        if udt_name == 'geometry':
            geom_column = column_name
        else:
            data_columns.append(column_name)

    return data_columns, geom_column

def get_data_table(layer_in_dataset, feature_ids = None, workslice_id = None):
    dataset = layer_in_dataset.dataset
    layer = layer_in_dataset.layer

    database_id = dataset.name
    cursor = connections[database_id].cursor()

    data_columns, geom_column = get_data_columns(cursor, layer.name)
    columns = ['st_asbinary(st_transform(st_setsrid(%s, %d), 4326)) AS geom' % (layer.geometry_expression, dataset.srid)]
    columns += ['"%s"."%s"' % (layer.name, c) for c in data_columns]
    feature_id_columns = {}
    attr_columns = list(data_columns)
    if layer.geometry_type == 'RELATION':
        for m in layer.members.select_related('member_layer').all():
            fid_col_name = "%s_feature_id" % m.table_alias
            columns.append('"%s"."%s" AS %s' % (m.table_alias, m.member_layer.pkey_name, fid_col_name))
            feature_id_columns[fid_col_name] = m.pk
            attr_columns.append(fid_col_name)

    sql_base = 'SELECT %s FROM "%s" %s' % (",".join(columns), layer.name, layer.join_sql)

    if feature_ids is not None:
        if len(feature_ids) > 0:
            sql_base += ' WHERE "%s"."%s" IN (%s)' % (layer.name, layer.pkey_name, ",".join([str(fid) for fid in feature_ids]))
        else:
            sql_base += ' WHERE "%s"."%s" IS NULL' % (layer.name, layer.pkey_name)

    sql_base += ' ORDER BY "%s"."%s" ASC' % (layer.name, layer.pkey_name)
    cursor.execute(sql_base)

    data_table = []

    for i,row in enumerate(cursor):
        if row[0] is None:
            continue
        row_geom = geos.GEOSGeometry(row[0])
        if row_geom.empty:
            continue

        row_data = dict(zip(attr_columns,[clean_data(c) for c in row[1:] ]))
        row_data['layer_name'] = layer.name
        row_data['dataset_name'] = dataset.name
        row_data['dataset_version'] = dataset.version

        if feature_id_columns:
            r = {}
            for col_name, member_id in feature_id_columns.iteritems():
                r[member_id] = row_data.pop(col_name)
            row_data['member_feature_ids'] = r

        if workslice_id is not None:
            row_data['workslice_id'] = workslice_id

        data_table.append((row_data, row_geom))

    return data_table


def _add_osm_nodes_from_overpass(layer, lid, data_table, osm_nodes):
    if layer.special_node_reuse_logic:
        node_match_json = overpass.osm_node_match_json(lid, data_table)['elements']
        for node in node_match_json:
            fid = node.get('tags', {}).get(layer.special_node_tag_name)
            if fid:
                osm_nodes[fid] = str(node['id'])

def _add_osm_ways_from_overpass(layer, lid, data_table, osm_nodes, osm_ways):
    if layer.special_way_reuse_logic:
        way_match_json = overpass.osm_way_match_json(lid, data_table)['elements']

        nodes = [e for e in way_match_json if e['type'] == 'node']
        ways = [e for e in way_match_json if e['type'] == 'way']

        for node in nodes:
            fid = node.get('tags', {}).get(layer.special_node_tag_name)
            if fid:
                osm_nodes[fid] = str(node['id'])

        reverse_osm_nodes = dict([(osm_id, fid) for (fid, osm_id) in osm_nodes.iteritems()])

        for way in ways:
            node_start = reverse_osm_nodes.get(str(way['nodes'][0]))
            node_end = reverse_osm_nodes.get(str(way['nodes'][-1]))
            way_name = way.get('tags', {}).get(layer.special_way_tag_name)
            if node_start and node_end and way_name:
                osm_ways[(node_start, way_name, node_end)] = str(way['id'])
            else:
                print "Failed to add: %s, %s, %s" % (node_start, way_name, node_end)

def export_custom(layer_in_dataset, feature_ids = None, workslice_id = None):
    dataset = layer_in_dataset.dataset
    layer = layer_in_dataset.layer

    layer_tags = layer_in_dataset.get_all_tags()
    processors = layer.get_processors()

    data_table = get_data_table(layer_in_dataset, feature_ids, workslice_id)
    member_data_tables = {}
    member_tags = {}

    osm_nodes = {}
    _add_osm_nodes_from_overpass(layer, layer_in_dataset, data_table, osm_nodes)
    osm_ways = {}
    _add_osm_ways_from_overpass(layer, layer_in_dataset, data_table, osm_nodes, osm_ways)

    for m in layer.members.select_related('member_layer').all():
        member_lid = dataset.layerindataset_set.get(layer=m.member_layer)
        member_feature_ids = [row_data['member_feature_ids'][m.pk] for (row_data, row_geom) in data_table]
        m_dt = get_data_table(member_lid, member_feature_ids, workslice_id)
        member_data_tables[m.pk] = m_dt
        member_tags[m.pk] = member_lid.get_all_tags()
        _add_osm_nodes_from_overpass(m.member_layer, member_lid, m_dt, osm_nodes)
        _add_osm_ways_from_overpass(m.member_layer, member_lid, m_dt, osm_nodes, osm_ways)

    writer = OSMCreateWriter(id_hash=(dataset.name, layer.name, feature_ids),
                       osm_nodes=osm_nodes,
                       osm_ways=osm_ways,
                       special_start_node_field_name=layer.special_start_node_field_name,
                       special_end_node_field_name=layer.special_end_node_field_name,
                       special_way_field_name=layer.special_way_field_name
                       )

    member_feature_map = {}

    # None of this happens unless the layer is a RELATION
    for m in layer.members.select_related('member_layer').all():
        m_layer = m.member_layer
        m_processors = m_layer.get_processors()
        for i, (row_data, row_geom) in enumerate(member_data_tables[m.pk]):
            db_feature_id = row_data[m_layer.pkey_name]
            db_table_name = m_layer.name
            if m_layer.geometry_type == 'POINT':
                osm_feature_type = 'node'
            elif m_layer.geometry_type == 'LINESTRING':
                osm_feature_type = 'way'
            else:
                raise NotImplementedError("We do not yet support %ss as members" % m_layer.geometry_type)
            key = (db_table_name, db_feature_id)
            # Reuse a member feature if already included as a different role.
            if key not in member_feature_map:
                osm_feature_ids = _export_custom_data_row(writer, m_layer, member_tags[m.pk], m_processors, i, row_data, row_geom)
                member_feature_map[key] = (osm_feature_type, osm_feature_ids)

    for i, (row_data, row_geom) in enumerate(data_table):
        member_refs = []
        for m in layer.members.select_related('member_layer').all():
            db_feature_id = row_data['member_feature_ids'][m.pk]
            db_table_name = m.member_layer.name
            key = (db_table_name, db_feature_id)
            osm_feature_type, osm_feature_ids = member_feature_map[key]
            for fid in osm_feature_ids:
                member_refs.append((m.role, osm_feature_type, fid))

        _export_custom_data_row(writer, layer, layer_tags, processors, i, row_data, row_geom, member_refs=member_refs)

    return writer.xml()

def _export_custom_data_row(writer, layer, tags, processors, i, row_data, row_geom, member_refs=None):
    row_tags = []
    for tag in tags:
        try:
            v = tag.eval(row_data)
        except tag.ScriptError, e:
            emsg = "Error evaluating '%s' tag against record:\n" % tag
            emsg += json.dumps(e.data, indent=2) + "\n"
            emsg += str(e)
            raise ValueError(emsg)
        if (v is not None) and (v != ""):
            row_tags.append((tag.tag, v, tag,))

    # apply geometry processing
    for p in processors:
        row_geom = p.process(row_geom, fields=row_data, tags=row_tags, id=i)

    if layer.special_node_reuse_logic:
        first_node_ref = str(row_data.get(layer.special_start_node_field_name))
        last_node_ref = str(row_data.get(layer.special_end_node_field_name))
    else:
        first_node_ref, last_node_ref = None, None
    if layer.special_way_reuse_logic:
        way_ref = str(row_data.get(layer.special_way_field_name))
    else:
        way_ref = None

    if layer.geometry_type == "RELATION":
        return writer.add_relation(row_tags, member_refs)
    elif row_geom:
        return writer.add_feature(row_geom, row_tags, first_node_ref, last_node_ref, way_ref)
    else:
        raise ValueError("Layer is not relation and no geometry found")

def int_or_none(obj):
    if isinstance(obj, (str, int, unicode)):
        return int(obj)
    else:
        return None

class OSMWriter(object):
    def xml(self):
        # prettify - ok to call more than once
        self._etree_indent(self.tree.getroot())

        s = StringIO()
        self.tree.write(s, 'utf-8')
        s.write('\n')
        return s.getvalue()

    def _etree_indent(self, elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            for e in elem:
                self._etree_indent(e, level+1)
            if not e.tail or not e.tail.strip():
                e.tail = i
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def wrap_longitude(lon):
    wrapped = (lon + 180) % 360 - 180
    if wrapped == -180 and lon >= 180:
        return 180
    else:
        return wrapped

def coords_for_next_way(coords, way_split_size):
    for pos in range(1, min(way_split_size, len(coords))):
        last_coords = coords[pos - 1]
        this_coords = coords[pos]

        # If this way spans over 180 degrees it must be taking the long way around
        last_lon_wrapped = wrap_longitude(last_coords[0])
        this_lon_wrapped = wrap_longitude(this_coords[0])

        if math.fabs(last_lon_wrapped - this_lon_wrapped) > 180:
            print "At pos %d got crossing of %f -> %f" % (pos, last_lon_wrapped, this_lon_wrapped)
            # Uh-oh!
            # We will end this way at the antimeridian, with an x of 180 or -180, then
            # start a new way with an equivalent value on the antimeridian on the other side
            if last_lon_wrapped == 180 or last_lon_wrapped == -180:
                if pos == 1:
                    print "Conveniently the first node is on the AM, so simply converting it and making a two-node way"
                    equiv_coords = (-last_lon_wrapped, last_coords[1])
                    cur_coords = [equiv_coords, coords[1]]
                    rem_coords = coords[1:]
                else:
                    print "Last position was on AM so finishing with that node"
                    # Generate an equivalent node and restart the way with that
                    equiv_coords = (-last_lon_wrapped, last_coords[1])
                    cur_coords = coords[:pos]
                    rem_coords = [equiv_coords] + coords[pos:]
            elif this_lon_wrapped == 180 or this_lon_wrapped == -180:
                print "This position on AM so generating an equivalent then finishing"
                # Generate an equivalent node, end the way with it, then restart
                equiv_coords = (-this_lon_wrapped, this_coords[1])
                cur_coords = coords[:pos] + [equiv_coords]
                rem_coords = coords[pos:]
            else:
                print "Interpolating"
                # Neither point is actually on the antimeridian, so need to interpolate,
                # End the way with that node, then restart with an equivalent
                if this_lon_wrapped > last_lon_wrapped: # Way is heading west
                    left_x = this_lon_wrapped - 180
                    left_y = this_coords[1]
                    right_x = last_lon_wrapped + 180
                    right_y = last_coords[1]
                else: # Way is heading east
                    left_x = last_lon_wrapped - 180
                    left_y = last_coords[1]
                    right_x = this_lon_wrapped + 180
                    right_y = this_coords[1]

                intersection_latitude = ((left_x * right_y) - (left_y * right_x)) / (left_x - right_x)

                if this_lon_wrapped > last_lon_wrapped: # Westbound
                    cur_coords = coords[:pos] + [(-180, intersection_latitude)]
                    rem_coords = [(180, intersection_latitude)] + coords[pos:]
                else:
                    cur_coords = coords[:pos] + [(180, intersection_latitude)]
                    rem_coords = [(-180, intersection_latitude)] + coords[pos:]

            return cur_coords, rem_coords

    # No intersections, so go until the way split size
    cur_coords = coords[:way_split_size]
    rem_coords = coords[way_split_size-1:]

    return cur_coords, rem_coords

class OSMCreateWriter(OSMWriter):
    WAY_SPLIT_SIZE = 495

    def __init__(self, id_hash=None, processors=None, osm_nodes={}, osm_ways={}, special_start_node_field_name=None, special_end_node_field_name=None, special_way_field_name=None):
        self.n_root = ElementTree.Element('osmChange', version="0.6", generator="linz2osm")
        self.n_create = ElementTree.SubElement(self.n_root, 'create', version="0.6", generator="linz2osm")
        self.tree = ElementTree.ElementTree(self.n_root)
        self._nodes = {}
        self._osm_nodes = osm_nodes
        self._osm_ways = osm_ways
        self.first_node_field = special_start_node_field_name
        self.last_node_field = special_end_node_field_name
        self.way_field = special_way_field_name

        if id_hash is None:
            self._id = 0
        else:
            h = hashlib.sha1(unicode(id_hash).encode('utf8')).hexdigest()
            self._id = -1 * int(h[:6], 16)

        self.processors = processors or []

    def add_feature(self, geom, tags=None, first_node_ref=None, last_node_ref=None, way_ref=None):
        return self.build_geom(geom, tags, first_node_ref, last_node_ref, way_ref)

    def add_relation(self, tags=None, member_refs=None):
        return self.build_rel(tags or [], member_refs or [])

    @property
    def next_id(self):
        """ Return a unique ID. """
        self._id -= 1
        return str(self._id)

    def build_polygon(self, geom, tags, root=None):
        if root is None:
            r = ElementTree.Element('relation', id=self.next_id)
            ElementTree.SubElement(r, 'tag', k='type', v='multipolygon')
            self.build_tags(r, tags, "relation")
        else:
            r = root

        if isinstance(geom, geos.MultiPolygon):
            for g in geom:
                self.build_polygon(g, tags, r)
        else:
            for i,ring in enumerate(geom):
                is_outer = (i == 0)
                w_tags = tags if is_outer else None
                w_ids = self.build_way(ring.tuple, w_tags)
                for w_id in w_ids:
                    ElementTree.SubElement(r, 'member', type="way", ref=w_id, role=('outer' if (i == 0) else 'inner'))

        if root is None:
            self.n_create.append(r)
        return [r.get('id')]


    # FIXME segments crossing antemeridian.
    def build_way(self, coords, tags, tag_nodes_at_ends=False, first_node_ref=None, last_node_ref=None, way_ref=None):
        if way_ref:
            "Way ref %s" % (str((first_node_ref, way_ref, last_node_ref)))
            w_id = self._osm_ways.get((first_node_ref, way_ref, last_node_ref))
            if not w_id:
                w_id = self._osm_ways.get((last_node_ref, way_ref, first_node_ref))
            if w_id:
                print "Reusing way: hit with w_id=%s" % str(w_id)
                return [w_id]
        ids = []
        rem_coords = [(wrap_longitude(x), y) for (x, y) in coords]
        special_node_type = "first" if tag_nodes_at_ends else None
        while True:
            w = ElementTree.Element('way', id=self.next_id)

            cur_coords, rem_coords = coords_for_next_way(rem_coords, self.WAY_SPLIT_SIZE)

            cur_coords_last_idx = len(cur_coords) - 1
            for i,c in enumerate(cur_coords):
                # Handle tagging special node types
                if tag_nodes_at_ends and not rem_coords:
                    if i == cur_coords_last_idx:
                        special_node_type = "last"

                n_id = None
                if tag_nodes_at_ends and special_node_type:
                    if special_node_type == "first":
                        node_ref = first_node_ref
                    elif special_node_type == "last":
                        node_ref = last_node_ref

                    if node_ref:
                        n_id = self._osm_nodes.get(node_ref)
                    if not n_id:
                        n_id = self._node(c, tags, True, special_node_type)
                        self._osm_nodes[node_ref] = n_id
                else:
                    n_id = self._node(c, None, True)
                special_node_type = None

                # Actually generate some XML now
                ElementTree.SubElement(w, 'nd', ref=n_id)
            self.build_tags(w, tags, "geometry")
            self.n_create.append(w)
            ids.append(w.get('id'))

            if len(rem_coords) < 2:
                break

        return ids

    def _node(self, coords, tags, map_node=True, special_node_type=None, osm_node=None):
        lat = coords[1]
        lon = wrap_longitude(coords[0])
        k = (str(lon), str(lat), id(tags) if tags else None)
        n = self._nodes.get(k)

        if (not map_node) or (n is None):
            n = ElementTree.SubElement(self.n_create, 'node', id=self.next_id, lat=str(lat), lon=str(lon))
            self.build_tags(n, tags, special_node_type)
            if map_node:
                self._nodes[k] = n
        return n.get('id')

    def build_node(self, geom, tags, map_node=True, node_ref=None):
        if node_ref:
            n_id = self._osm_nodes.get(node_ref)
            if n_id:
                return [n_id]
        return [self._node((geom.x, geom.y), tags, map_node, "geometry")]

    def build_geom(self, geom, tags, first_node_ref, last_node_ref, way_ref, inner=False):
        if isinstance(geom, geos.Polygon) and (len(geom) == 1) and (len(geom[0]) <= self.WAY_SPLIT_SIZE):
            # short single-ring polygons are built as ways
            return self.build_way(geom[0].tuple, tags)

        elif isinstance(geom, (geos.MultiPolygon, geos.Polygon)):
            return self.build_polygon(geom, tags)

        elif isinstance(geom, geos.GeometryCollection):
            # FIXME: Link together as a relation?
            ids = []
            for g in geom:
                ids += self.build_geom(g, tags, first_node_ref, last_node_ref, way_ref, inner=True)
            return ids

        elif isinstance(geom, geos.Point):
            # node
            # indepenent nodes are mapped (ie. POINTs)
            # repeated nodes within a MULTIPOINT/GEOMETRYCOLLECTION are mapped
            return self.build_node(geom, tags, map_node=inner, node_ref=first_node_ref)

        elif isinstance(geom, geos.LineString):
            # way
            return self.build_way(geom.tuple, tags, True, first_node_ref, last_node_ref, way_ref)

    def build_rel(self, tags, member_refs):
        r = ElementTree.Element('relation', id=self.next_id)

        for (role, ftype, ref) in member_refs:
            ElementTree.SubElement(r, 'member', type=ftype, ref=ref, role=role)

        self.build_tags(r, tags, "relation")
        self.n_create.append(r)
        return [r.get('id')]

    def build_tags(self, parent_node, tags, object_type):
        if tags:
            applied_tags = set()
            for tn, tv, tag_obj in tags:
                if tag_obj.apply_for(object_type):
                    if tn not in applied_tags:
                        applied_tags.add(tn)
                        if len(tn) > 255:
                            raise ValueError(u'Tag key too long (max. 255 chars): %s' % tn)
                        tv = unicode(tv)
                        if len(tv) > 255:
                            raise ValueError(u'Tag value too long (max. 255 chars): %s' % tv)
                        ElementTree.SubElement(parent_node, 'tag', k=tn, v=tv)

def export_delete(layer_in_dataset, nodes, ways, relations):
    writer = OSMDeleteWriter()
    print "Deleting %d nodes, %d ways, %d relations..." % (len(nodes), len(ways), len(relations))
    for node in nodes:
        writer.remove_node(node)
    for way in ways:
        writer.remove_way(way)
    for relation in relations:
        writer.remove_relation(relation)
    return writer.xml()

class OSMDeleteWriter(OSMWriter):
    def __init__(self):
        self.n_root = ElementTree.Element('osmChange', version="0.6", generator="linz2osm")
        self.n_delete = ElementTree.SubElement(self.n_root, 'delete', version="0.6", generator="linz2osm")
        self.tree = ElementTree.ElementTree(self.n_root)

    def remove_node(self, node):
        ElementTree.SubElement(self.n_delete, 'node', version=str(node['version']), changeset=str(node['changeset']), id=str(node['id']), lat=str(node['lat']), lon=str(node['lon']))
        print "   ... node %s" % node['id']

    def remove_way(self, way):
        ElementTree.SubElement(self.n_delete, 'way', version=str(way['version']), changeset=str(way['changeset']), id=str(way['id']))

    def remove_relation(self, relation):
        ElementTree.SubElement(self.n_delete, 'relation', version=str(relation['version']), changeset=str(relation['changeset']), id=str(relation['id']))
