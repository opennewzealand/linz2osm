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

import decimal
import re

from datetime import datetime
from dateutil.relativedelta import relativedelta
from fractions import Fraction
from textwrap import dedent

from django.core.urlresolvers import reverse
from django.db import transaction, connections
from django.conf import settings
from django.utils import text
from django.contrib import auth
from django.contrib.gis import geos
from django.contrib.gis.db import models

from linz2osm.data_dict.models import Layer, Dataset, LayerInDataset
from linz2osm.workslices import tasks
from linz2osm.convert import osm, overpass

CELL_RE = re.compile(r'\AX(?P<x>[0-9-]+)Y(?P<y>[0-9-]+)C(?P<cpd>[0-9]+)\Z')

class Cell(object):
    def __init__(self, text_form):
        self.x, self.y, self.cpd = (int(i) for i in CELL_RE.match(text_form).group('x', 'y', 'cpd'))
        self.lon = self.x / float(self.cpd)
        self.lat = self.y / float(self.cpd)
        self.size = 1.0 / float(self.cpd)

    def as_polygon(self):
        return geos.Polygon.from_bbox((self.lon, self.lat, self.lon + self.size, self.lat + self.size))

    def __unicode__(self):
        return "X: %f, Y: %f, CPD: %d" % (self.lon, self.lat, self.cpd)

class WorksliceFeatureFilter(object):
    def __init__(self, layer_in_dataset):
        self.layer_in_dataset = layer_in_dataset

class AllFilter(WorksliceFeatureFilter):
    def apply(self, workslice_features):
        return workslice_features

class NoConflictFilter(WorksliceFeatureFilter):
    def apply(self, workslice_features):
        osm_conflicts = osm.featureset_conflicts(self.layer_in_dataset, workslice_features)
        passed = []
        for (wf, conflicts_json) in osm_conflicts:
            if not conflicts_json['elements']:
                passed.append(wf)
        return passed

class WorksliceManager(models.GeoManager):
    def create_workslice(self, layer_in_dataset, user, extent=None, filter_name=None):
        if filter_name == 'noconflicts':
            feature_filter = NoConflictFilter(layer_in_dataset)
        else:
            feature_filter = AllFilter(layer_in_dataset)

        try:
            with transaction.commit_on_success():
                # print "original extent"
                # print extent.ewkt

                # Get extent to use to get features (no clipping)
                allocation_extent = extent or geos.MultiPolygon(layer_in_dataset.extent)
                if allocation_extent.geom_type == 'Polygon':
                    allocation_extent = geos.MultiPolygon(allocation_extent)
                allocation_extent.srid = 4326

                # Get extent to show on map
                existing_checkouts = self.exclude(state__in=('draft', 'abandoned')).filter(layer_in_dataset=layer_in_dataset).unionagg()
                display_extent = allocation_extent.clone()
                if existing_checkouts is not None:
                    display_extent = display_extent.difference(existing_checkouts)
                display_extent = display_extent.intersection(layer_in_dataset.translated_extent)
                if display_extent.geom_type == 'Polygon':
                    display_extent = geos.MultiPolygon(display_extent)
                elif display_extent.geom_type != 'MultiPolygon':
                    # make a tiny circular checkout at the centroid of the checkout
                    display_extent = geos.MultiPolygon(extent.centroid.buffer(0.0000012345))

                display_extent.srid = 4326

                # print "allocation extent"
                # print allocation_extent.ewkt
                # print "display extent"
                # print display_extent.ewkt

                # Get features
                workslice = self.create(layer_in_dataset = layer_in_dataset,
                                        checkout_extent = display_extent,
                                        user = user,
                                        state = 'processing',
                                        checked_out_at = datetime.now(),
                                        status_changed_at = datetime.now(),
                                        followup_deadline = datetime.now() + relativedelta(months = +2),
                                        )
                workslice.save()
                WorksliceFeature.objects.allocate_workslice_features(workslice, allocation_extent, feature_filter)
        except WorksliceTooFeaturefulError, e:
            raise e
        except WorksliceInsufficientlyFeaturefulError, e:
            raise e
        else:
            tasks.osm_export.delay(workslice)
            return workslice


class Workslice(models.Model):
    STATES = [
        ('draft', 'Draft'),            # While the user is still selecting dataset, layer & extent
        ('processing', 'Processing'),  # While we are generating the osmChange file
        ('out', 'Checked Out'),        # While a user is merging the data
        ('abandoned', 'Abandoned'),    # If a user has decided not to merge the data
        ('blocked', 'Blocked'),        # If a user wants to wait for a while before continuing
        ('complete', 'Completed'),     # User has marked the workslice as merged into OSM
    ]
    STATES_LOOKUP = dict(STATES)
    TRANSITIONS = {
        'draft': [('processing', 'Process')],
        'processing': [],
        'out': [('abandoned', 'Abandon'), ('blocked', 'Mark Blocked'), ('complete', 'Mark Complete')],
        'abandoned': [],
        'blocked': [('abandoned', 'Abandon'), ('out', 'Unblock'), ('complete', 'Mark Complete')],
        'complete': [('abandoned', 'Abandon')],
        }
    state = models.CharField(max_length=30, choices=STATES)
    checked_out_at = models.DateTimeField(null=True, blank=True, db_index=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    followup_deadline = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(auth.models.User)
    layer_in_dataset = models.ForeignKey(LayerInDataset)
    version = models.TextField(blank=True)
    checkout_extent = models.MultiPolygonField()
    feature_count = models.IntegerField(null=True)
    file_size = models.IntegerField(null=True)
    # FIXME: store file name so changes won't mess it up

    @property
    def name(self):
        return "%d-%s-%s-%s" % (self.id, self.layer_in_dataset.layer.name, self.layer_in_dataset.dataset.name, self.user.username)

    def acceptable_transitions(self):
        return self.__class__.TRANSITIONS[self.state]

    @models.permalink
    def get_absolute_url(self):
        return ('linz2osm.workslices.views.show_workslice', (), {'workslice_id': self.id})

    def friendly_status(self):
        # FIXME get_status_display()
        return self.__class__.STATES_LOOKUP[self.state]

    def post_checkout_status(self):
        return self.state in ['abandoned', 'blocked', 'complete']

    def js_feature_geojson(self):
        return """ {
            "geometry": %s,
            "type": "Feature",
            "properties": {
                "model": "Workslice",
                "state": "%s",
                "id": "%d"
            }
        } """ %  (self.checkout_extent.geojson, self.state, self.id)

    @property
    def type_description(self):
        return "Workslice"

    @property
    def type_url(self):
        return reverse('linz2osm.workslices.views.list_workslices')

    @property
    def osm_link(self):
        if self.checkout_extent:
            return "http://www.openstreetmap.org/index.html?minlon=%f&minlat=%f&maxlon=%f&maxlat=%f&box=yes" % self.checkout_extent.extent
        else:
            return "http://www.openstreetmap.org/index.html"

    objects = WorksliceManager()


class WorksliceTooFeaturefulError(Exception):
    pass

class WorksliceInsufficientlyFeaturefulError(Exception):
    pass

class WorksliceFeatureManager(models.Manager):
    def allocate_workslice_features(self, workslice, extent, feature_filter):
        layer_in_dataset = workslice.layer_in_dataset
        covered_fids = osm.get_layer_feature_ids(layer_in_dataset, extent)
        if covered_fids is None:
            raise WorksliceTooFeaturefulError
        if len(covered_fids) == 0:
            raise WorksliceInsufficientlyFeaturefulError

        ws_feats = [
            WorksliceFeature(
                workslice=workslice,
                layer_in_dataset=layer_in_dataset,
                feature_id=fid
                ) for fid
            in covered_fids
            if not self.filter(
                layer_in_dataset=layer_in_dataset,
                feature_id=fid,
                dirty=0
                ).exists()
            ]
        if len(ws_feats) > layer_in_dataset.layer.feature_limit:
            raise WorksliceTooFeaturefulError
        if len(ws_feats) == 0:
            raise WorksliceInsufficientlyFeaturefulError
        ws_feats = feature_filter.apply(ws_feats)
        self.bulk_create(ws_feats)
        workslice.feature_count = len(ws_feats)
        workslice.save()

INDIV_CONFLICT_PROXIMITY = 0.0001

class WorksliceFeature(models.Model):
    objects = WorksliceFeatureManager()

    workslice = models.ForeignKey(Workslice)
    feature_id = models.IntegerField(db_index=True)
    layer_in_dataset = models.ForeignKey(LayerInDataset)
    dirty = models.IntegerField(default=0, choices=(
            (0, 'no',),
            (1, 'deleted',),
            (2, 'updated',),
            ))

    def wgs_geom(self, expression = "ST_Transform(%s, 4326)"):
        cursor = connections[self.layer_in_dataset.dataset.name].cursor()
        layer = self.layer_in_dataset.layer
        cursor.execute("""
            SELECT ST_AsHexEWKB(%(expression)s)
            FROM %(layer_name)s
            %(join_sql)s
            WHERE %(layer_name)s.%(pkey_name)s = %(feature_id)d
            """ % {
                'expression': expression % layer.geometry_expression,
                'layer_name': layer.name,
                'join_sql': layer.join_sql,
                'pkey_name': layer.pkey_name,
                'feature_id': self.feature_id,
        })
        return geos.GEOSGeometry(cursor.fetchone()[0])

    def wgs_bounds(self):
        return self.wgs_geom(expression="ST_Envelope(ST_Transform(%s, 4326))")

    def wgs_geojson(self, centroid_only=False):
        geom = self.wgs_geom()
        if centroid_only:
            geom = geom.centroid

        return """ {
            "geometry": %s,
            "type": "Feature",
            "properties": {
                "model": "LayerInDataset"
            }
        } """ % geom.geojson

    def osm_individual_conflict_query_ql(self, query_data):
        return self.osm_conflicts_query_ql(query_data, INDIV_CONFLICT_PROXIMITY)

    def osm_conflicts_query_ql(self, tags_ql, proximity = overpass.OVERPASS_PROXIMITY):
        geotype = self.layer_in_dataset.layer.geometry_type
        if geotype == "POINT":
            query = dedent("""
                node
                %(tags)s
                %(bounds)s;
                """)
        elif geotype == "LINESTRING":
            query = dedent("""
                (
                way
                %(tags)s
                %(bounds)s;
                >;
                );""")
        elif geotype == "POLYGON":
            query = dedent("""
                (
                rel
                ["type"="multipolygon"]
                %(tags)s
                %(bounds)s;
                way
                %(tags)s
                %(bounds)s;
                >;
                );""")
        elif geotype == "RELATION":
            query = dedent("""
                (
                rel
                %(tags)s
                %(bounds)s;
                >;
                );""")
        else:
            raise ValueError("Unsupported geometry type %s" % geotype)

        geobounds = self.wgs_bounds().extent
        str_bounds = overpass.str_bounds_for(geobounds, proximity)

        return query % {
            'tags': tags_ql,
            'bounds': str_bounds,
            }

