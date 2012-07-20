from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils import simplejson, text
from django.conf import settings
from django import forms

from linz2osm.data_dict.models import Layer, Dataset
from linz2osm.workslices.models import Workslice

def show_workslice(request, workslice_id=None):
    workslice = get_object_or_404(Workslice, pk=workslice_id)
    ctx = {
        'workslice_id': workslice_id,
        'workslice': workslice,
        'title': 'Workslice #%d' % workslice.id,
        'status_name': workslice.friendly_status(),
        'post_checkout_status': workslice.post_checkout_status(),
        'file_name': "%s.osc" % workslice.name,
        'file_path': "%s%s.osc" % (settings.MEDIA_URL, workslice.name),
    }

    return render_to_response('workslices/show.html', ctx, context_instance=RequestContext(request))

def new_workslice(request, layer_name, dataset_name):
    ctx = {
        'layer_name': layer_name,
        'dataset_name': 'FIXME',
    }
    return render_to_response('workslices/new.html', ctx, context_instance=RequestContext(request))
