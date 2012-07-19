import decimal
from datetime import datetime
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.db import models
from django.utils import text
from django.contrib import auth
from django.contrib import gis

from linz2osm.data_dict.models import Layer
from linz2osm.workslices import tasks

class WorksliceManager(models.Manager):
    def create_workslice(self, layer, dataset, bounds, user):
        workslice = self.create(layer = layer,
                                dataset = dataset,
                                bounds = bounds,
                                user = user,
                                state = 'processing',
                                checked_out_at = datetime.now(),
                                status_changed_at = datetime.now(),
                                followup_deadline = datetime.now() + relativedelta(months = +2),
                                )
        workslice.save()
        workslice.name = "%d-%s-%s-%s" % (workslice.id, layer.name, dataset, user.username)
        workslice.save()
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
    name = models.CharField(max_length=255, unique=True, help_text='Unique identifier for this workslice, also used to form the filename')
    state = models.CharField(max_length=30, choices=STATES)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    followup_deadline = models.DateTimeField(null=True, blank=True)
    layer = models.ForeignKey(Layer)
    user = models.ForeignKey(auth.models.User)
    dataset = models.CharField(max_length=255)
    bounds = models.CharField(max_length=255, null=True)
    # extent = gis.db.models.PolygonField(geography=True)

    @models.permalink
    def get_absolute_url(self):
        return ('linz2osm.workslices.views.show_workslice', (), {'workslice_id': self.id})
    
    def friendly_status(self):
        return self.__class__.STATES_LOOKUP[self.state]
    
    objects = WorksliceManager()

