from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.conf import settings
from django import forms
from django.contrib import auth

from linz2osm.data_dict.models import Layer, Dataset
from linz2osm.workslices.models import Workslice

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
    
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
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = auth.authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            if user is not None:
                if user.is_active:
                    auth.login(request, user)
                    response = HttpResponse()
                    response.status_code = 303
                    response['Location'] = '/'
                    return response
    else:
        form = LoginForm()
    ctx['form'] = form
    return render_to_response('lobby/login.html', ctx, context_instance=RequestContext(request))

def logout(request):
    auth.logout(request)
    ctx = {}
    return render_to_response('lobby/logout.html', ctx, context_instance=RequestContext(request))

    
