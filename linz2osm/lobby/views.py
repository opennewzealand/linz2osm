#  LINZ-2-OSM
#  Copyright (C) 2010-2012 Koordinates Ltd.
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
        'datasets': Dataset.objects.order_by('description').all(),
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

    
