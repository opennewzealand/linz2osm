from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils import simplejson, text
from django.conf import settings
from django import forms

from linz2osm.data_dict.models import Layer
from linz2osm.workslices.models import Workslice

DATASETS = dict([(k,v['_description']) for k,v in settings.DATABASES.items() if k != 'default'])

def show_workslice(request, workslice_id=None):
    workslice = get_object_or_404(Workslice, pk=workslice_id)
    ctx = {
        'workslice_id': workslice_id,
        'dataset_name': DATASETS[workslice.dataset],
        'title': 'Workslice #%d' % workslice.id,
        'user_name': workslice.user.username,
        'layer_name': workslice.layer.name,
        'status_name': workslice.friendly_status(),
        'file_name': "%s.osc" % workslice.name,
        'file_path': "%s%s.osc" % (settings.MEDIA_URL, workslice.name),
    }

    return render_to_response('workslices/show.html', ctx, context_instance=RequestContext(request))

