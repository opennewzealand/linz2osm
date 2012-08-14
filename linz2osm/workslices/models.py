import decimal
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fractions import Fraction

from django.db import transaction
from django.conf import settings
from django.utils import text
from django.contrib import auth
from django.contrib import gis
from django.contrib.gis.db import models

from linz2osm.data_dict.models import Layer, Dataset, LayerInDataset
from linz2osm.workslices import tasks
from linz2osm.convert import osm

CELL_RE = re.compile(r'\AX(?P<x>[0-9-]+)Y(?P<y>[0-9-]+)C(?P<cpd>[0-9]+)\Z')

class Cell(object):
    def __init__(self, text_form):
        self.x, self.y, self.cpd = (int(i) for i in CELL_RE.match(text_form).group('x', 'y', 'cpd'))
        self.lon = self.x / float(self.cpd)
        self.lat = self.y / float(self.cpd)
        self.size = 1.0 / float(self.cpd)

    def as_polygon(self):
        return gis.geos.Polygon.from_bbox((self.lon, self.lat, self.lon + self.size, self.lat + self.size))

    def __unicode__(self):
        return "X: %f, Y: %f, CPD: %d" % (self.lon, self.lat, self.cpd)

FEATURE_LIMIT = 1000
    
class WorksliceManager(models.GeoManager):
    def create_workslice(self, layer_in_dataset, user, extent=None):
        try:
            with transaction.commit_on_success():
                finished_extent = extent or gis.geos.MultiPolygon(layer_in_dataset.extent)
                existing_checkouts = self.exclude(state__in=('draft', 'abandoned')).filter(layer_in_dataset=layer_in_dataset).unionagg()
                if existing_checkouts is not None:
                    finished_extent = finished_extent.difference(existing_checkouts)
                finished_extent = finished_extent.intersection(layer_in_dataset.extent)
                if finished_extent.geom_type == 'Polygon':
                    finished_extent = gis.geos.MultiPolygon(finished_extent)
                workslice = self.create(layer_in_dataset = layer_in_dataset,
                                        checkout_extent = finished_extent,
                                        user = user,
                                        state = 'processing',
                                        checked_out_at = datetime.now(),
                                        status_changed_at = datetime.now(),
                                        followup_deadline = datetime.now() + relativedelta(months = +2),
                                        )
                workslice.save()
                WorksliceFeature.objects.allocate_workslice_features(workslice)
        except WorksliceTooFeaturefulError, e:
            raise e
        except WorksliceInsufficientlyFeaturefulError, e:
            raise e
        else:
            # TODO: also have a task to bulk restart these should celery fall over
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
        'complete': [('abandon', 'Abandon')],
        }
    state = models.CharField(max_length=30, choices=STATES)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    followup_deadline = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(auth.models.User)
    layer_in_dataset = models.ForeignKey(LayerInDataset)
    checkout_extent = models.MultiPolygonField()
    feature_count = models.IntegerField(null=True)
    file_size = models.IntegerField(null=True)

    
    @property
    def name(self):
        return "%d-%s-%s-%s" % (self.id, self.layer_in_dataset.layer.name, self.layer_in_dataset.dataset.name, self.user.username)

    def acceptable_transitions(self):
        return self.__class__.TRANSITIONS[self.state]
    
    def formatted_feature_id_list(self):
        return ",".join(str(wf.feature_id) for wf in self.workslicefeature_set.all())
    
    @models.permalink
    def get_absolute_url(self):
        return ('linz2osm.workslices.views.show_workslice', (), {'workslice_id': self.id})
    
    def friendly_status(self):
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
        
    objects = WorksliceManager()

class WorksliceTooFeaturefulError(Exception):
    pass

class WorksliceInsufficientlyFeaturefulError(Exception):
    pass
    
class WorksliceFeatureManager(models.Manager):
    def allocate_workslice_features(self, workslice):
        layer_in_dataset = workslice.layer_in_dataset
        covered_fids = osm.get_layer_feature_ids(layer_in_dataset, workslice.checkout_extent, FEATURE_LIMIT)
        if covered_fids is None:
            raise WorksliceTooFeaturefulError
        if len(covered_fids) == 0:
            raise WorksliceInsufficientlyFeaturefulError

        ws_feats = [
            WorksliceFeature(
                workslice=workslice,
                layer_in_dataset=layer_in_dataset,
                feature_id=ogc_fid
                ) for ogc_fid
            in covered_fids
            if not self.filter(
                layer_in_dataset=layer_in_dataset,
                feature_id=ogc_fid
                ).exists()
            ]
        self.bulk_create(ws_feats)
        workslice.feature_count = len(ws_feats)
        workslice.save()
    
class WorksliceFeature(models.Model):
    objects = WorksliceFeatureManager()
    
    workslice = models.ForeignKey(Workslice)
    feature_id = models.IntegerField()
    layer_in_dataset = models.ForeignKey(LayerInDataset)
