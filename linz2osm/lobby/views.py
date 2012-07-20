from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.conf import settings
from django import forms

from linz2osm.data_dict.models import Layer, Dataset
from linz2osm.workslices.models import Workslice

# Create your views here.
def home_page(request):
    ctx = {
        'datasets': Dataset.objects.all(),
        }
    return render_to_response('lobby/home_page.html', ctx, context_instance=RequestContext(request))

def dashboard(request):
    ctx = {}
    return render_to_response('lobby/dashboard.html', ctx, context_instance=RequestContext(request))

def login(request):
    ctx = {}
    return render_to_response('lobby/login.html', ctx, context_instance=RequestContext(request))

def logout(request):
    ctx = {}
    return render_to_response('lobby/logout.html', ctx, context_instance=RequestContext(request))

    
