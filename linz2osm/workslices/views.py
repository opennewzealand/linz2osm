# -*- coding: utf-8 -*-
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

from datetime import datetime

import re
import json
import django.db

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils import simplejson, text
from django.conf import settings
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.contrib.auth.models import User
from django import forms

from linz2osm.data_dict.models import *
from linz2osm.workslices.models import *
from linz2osm.convert import osm, overpass
from linz2osm.utils.forms import BootstrapErrorList

def show_workslice(request, workslice_id=None):
    workslice = get_object_or_404(Workslice, pk=workslice_id)
    # FIXME: just need a workslice
    ctx = {
        'workslice_id': workslice_id,
        'workslice': workslice,
        'layer_in_dataset': workslice.layer_in_dataset,
        'title': 'Workslice #%d' % workslice.id,
        'status_name': workslice.friendly_status(),
        'post_checkout_status': workslice.post_checkout_status(),
        'file_name': "%s.osc" % workslice.name,
        'file_path': "%s%s.osc" % (settings.MEDIA_URL, workslice.name),
        'form': WorksliceUpdateForm(error_class=BootstrapErrorList),
    }

    return render_to_response('workslices/show.html', ctx, context_instance=RequestContext(request))

class WorksliceUpdateForm(forms.Form):
    transition = forms.CharField(widget=forms.HiddenInput(), required=True)

def update_workslice(request, workslice_id=None):
    workslice = get_object_or_404(Workslice, pk=workslice_id)
    # FIXME: just need a workslice
    ctx = {
        'workslice_id': workslice_id,
        'workslice': workslice,
        'layer_in_dataset': workslice.layer_in_dataset,
        'title': 'Workslice #%d' % workslice.id,
        'status_name': workslice.friendly_status(),
        'post_checkout_status': workslice.post_checkout_status(),
        'file_name': "%s.osc" % workslice.name,
        'file_path': "%s%s.osc" % (settings.MEDIA_URL, workslice.name),
    }
    
    if request.method == 'POST':
        form = WorksliceUpdateForm(request.POST, error_class=BootstrapErrorList)
        if form.is_valid():
            if not request.user.is_authenticated():
                return HttpResponseRedirect('/login/')
            if not (request.user.is_superuser or (request.user == workslice.user)):
                form._errors["__all__"] = form.error_class([u"You do not own this workslice"])
            else:
                transition = form.cleaned_data['transition']
                for t in workslice.acceptable_transitions():
                    if t[0] == transition:
                        workslice.state = transition
                        workslice.status_changed_at = datetime.now() 
                        if transition == "abandoned":
                            workslice.workslicefeature_set.all().delete()
                        workslice.save()
                        return HttpResponseRedirect(workslice.get_absolute_url())
                form._errors["__all__"] = form.error_class([u"Not allowed to make this workslice '%s'" % transition])
    else:
        form = WorksliceUpdateForm(error_class=BootstrapErrorList)
    ctx['form'] = form
    return render_to_response('workslices/show.html', ctx, context_instance=RequestContext(request))

SORT_CHOICES = [
    ( 'checked_out_at', 'Checked Out ↑',),
    ( '-checked_out_at', 'Checked Out ↓',),
    ( 'user', 'User ↑',),
    ( '-user', 'User ↓',),
    ( 'feature_count', 'Features ↑',),
    ( '-feature_count', 'Features ↓',),
    ( 'state', 'State ↑',),
    ( '-state', 'State ↓',),
]

class WorksliceFilterForm(forms.Form):
    ws_state = forms.TypedChoiceField(choices=[['', '----------']] + Workslice.STATES, required=False, initial='', label='State')
    dataset = forms.ModelChoiceField(queryset=Dataset.objects.order_by('description').all(), required=False)
    layer = forms.ModelChoiceField(queryset=Layer.objects.order_by('name').all(), required=False)
    user = forms.ModelChoiceField(queryset=User.objects.order_by('username').all(), required=False)
    order_by = forms.TypedChoiceField(choices=SORT_CHOICES, required=False, initial='-checked_out_at', label='Order by')

    @property
    def uri_components(self):
        return "".join(["&%s=%s" % (name, value) for name, value in self.data.iteritems() if name != 'page'])

WORKSLICES_PER_PAGE = 15
    
def list_workslices(request, username=None):
    workslices = Workslice.objects
    form = WorksliceFilterForm(request.GET)
    if username:
        user = get_object_or_404(User, username=username)
        workslices = workslices.filter(user=user)
    if form.is_valid():
        if form.cleaned_data['ws_state']:
            workslices = workslices.filter(state=form.cleaned_data['ws_state'])
        if form.cleaned_data['dataset']:
            workslices = workslices.filter(layer_in_dataset_id__in=[lid.id for lid in LayerInDataset.objects.filter(dataset=form.cleaned_data['dataset'])])
        if form.cleaned_data['layer']:
            workslices = workslices.filter(layer_in_dataset_id__in=[lid.id for lid in LayerInDataset.objects.filter(layer=form.cleaned_data['layer'])])
        if form.cleaned_data['user']:
            workslices = workslices.filter(user=form.cleaned_data['user'])
        if form.cleaned_data['order_by']:
            workslices = workslices.order_by(form.cleaned_data['order_by'])
        else:
            workslices = workslices.order_by('-checked_out_at')
    else:
        workslices = workslices.order_by('checked_out_at')
    paginator = Paginator(workslices, WORKSLICES_PER_PAGE)
    page = request.GET.get('page')
    try:
        display_workslices = paginator.page(page)
    except PageNotAnInteger:
        display_workslices = paginator.page(1)
    except EmptyPage:
        display_workslices = paginator.page(paginator.num_pages)
        
    ctx = {
        'workslices': display_workslices,
        'form': form,
    }
    return render_to_response('workslices/list.html', ctx, context_instance=RequestContext(request))

class WorksliceForm(forms.Form):
    cells = forms.CharField(widget=forms.HiddenInput(), required=False)
    show_features_in_selection = forms.ChoiceField(choices=(
            ('no', 'No, count only'),
            ('yes', 'Yes'),
            ('centroids', 'Centroids'),
            ), initial='centroids')
    show_conflicting_features = forms.ChoiceField(choices=(
            ('no', 'No'),
            ('yes', 'Yes'),
            ('count', "Count but don't show"),
            ), initial='no')
    feature_filter = forms.ChoiceField(choices=(
            ('all', 'All'),
            ('noconflicts', 'No OSM conflicts'),
            ), initial='all')

    def __init__(self, *args, **kwargs):
        hide_filters = kwargs.pop('hide_filters', None)
        super(WorksliceForm, self).__init__(*args, **kwargs)
        if hide_filters:
            self.fields['feature_filter'].widget = forms.HiddenInput()
    
    def clean(self):
        cleaned_data = super(WorksliceForm, self).clean()
        data = cleaned_data.get('cells')
        if data is None or data == '':
            raise forms.ValidationError('You must select at least one cell.')
        cells = [Cell(t) for t in data.split("_")]
        self.extent = MultiPolygon([c.as_polygon() for c in cells]).cascaded_union
        self.extent.srid = 4326
        self.num_cells = len(cells)
        if not (isinstance(self.extent, Polygon)):
            raise forms.ValidationError('Extent must be contiguous and not cross anti-meridian.')
        if self.extent.num_interior_rings > 0:
            raise forms.ValidationError('Extent must not have interior holes.')        
        return cleaned_data
    
    
def create_workslice(request, layer_in_dataset_id):
    layer_in_dataset = get_object_or_404(LayerInDataset, pk=layer_in_dataset_id)
    layer = layer_in_dataset.layer
    dataset = layer_in_dataset.dataset
    
    ctx = {
        'layer_in_dataset': layer_in_dataset,
        'workslices': layer_in_dataset.workslice_set.all(),
        'title': "%s - %s" % (dataset.description, layer.name),
    }
    if request.method == 'POST':
        if not request.user.is_authenticated():
            return HttpResponseRedirect('/login/')
        form = WorksliceForm(request.POST, error_class=BootstrapErrorList, hide_filters=layer_in_dataset.hide_filters)
        if form.is_valid():
            try:
                workslice = Workslice.objects.create_workslice(layer_in_dataset, request.user, form.extent, form.cleaned_data['feature_filter'])
            except osm.Error, e:
                ctx['error'] = str(e)
            except WorksliceTooFeaturefulError, e:
                form._errors["__all__"] = form.error_class([u"Too many features in selection (over %d): Please reduce selection" % layer.feature_limit])
            except WorksliceInsufficientlyFeaturefulError, e:
                form._errors["__all__"] = form.error_class([u"No features in selection"])
            else:
                response = HttpResponse()
                response.status_code = 303
                response['Location'] = workslice.get_absolute_url()
                return response
            pass
    else:
        form = WorksliceForm(error_class=BootstrapErrorList, hide_filters=layer_in_dataset.hide_filters)
    ctx['form'] = form
    return render_to_response('workslices/create.html', ctx, context_instance=RequestContext(request))

def workslice_info(request, layer_in_dataset_id):
    layer_in_dataset = get_object_or_404(LayerInDataset, pk=layer_in_dataset_id)
    layer = layer_in_dataset.layer
    dataset = layer_in_dataset.dataset
    
    ctx = {}
    
    form = WorksliceForm(request.POST, error_class=BootstrapErrorList, hide_filters=layer_in_dataset.hide_filters)
    if form.is_valid():
        feature_count = osm.get_layer_feature_count(dataset.name, layer, form.extent)
        if feature_count > layer.feature_limit:
            ctx['info'] = "Too many features (over %d): please reduce selection." % layer.feature_limit
            ctx['osm_conflict_info'] = ""
        else:
            if feature_count > 1:
                ctx['info'] = "%d features in selection." % feature_count
            elif feature_count == 1:
                ctx['info'] = "1 feature in selection."
            elif feature_count == 0:
                ctx['info'] = "No features in selection."
            else:
                ctx['info'] = "Serious error calculating features."

            if form.cleaned_data['show_conflicting_features'] in ['yes', 'count'] or form.cleaned_data['show_features_in_selection'] in ['yes', 'centroids']:
                feature_ids = osm.get_layer_feature_ids(layer_in_dataset, form.extent)
                workslice_features = [WorksliceFeature(feature_id=feat_id, layer_in_dataset=layer_in_dataset) for feat_id in feature_ids]

            if form.cleaned_data['show_conflicting_features'] in ['yes', 'count']:
                if layer.tags_ql:
                    osm_conflicts = overpass.osm_conflicts_json(workslice_features, layer.tags_ql)['elements'] # FIXME: tagging
                
                    nodes = dict([(n['id'], n) for n in osm_conflicts if n['type'] == 'node'])
                    ways = dict([(n['id'], n) for n in osm_conflicts if n['type'] == 'way'])
                    rels = dict([(n['id'], n) for n in osm_conflicts if n['type'] == 'rel'])

                    if layer.geometry_type == 'POINT':
                        conflict_count = len(nodes)
                        if form.cleaned_data['show_conflicting_features'] == 'yes':
                            ctx['osm_conflict_geometry'] = overpass.osm_geojson(nodes.values())
                    elif layer.geometry_type == 'LINESTRING':
                        conflict_count = len(ways)
                        if form.cleaned_data['show_conflicting_features'] == 'yes':
                            ctx['osm_conflict_geometry'] = overpass.osm_geojson(ways.values(), nodes)
                    elif layer.geometry_type == 'POLYGON':
                        conflict_count = len(ways) # FIXME: count rels too.
                        if form.cleaned_data['show_conflicting_features'] == 'yes':
                            ctx['osm_conflict_geometry'] = overpass.osm_geojson(rels.values(), nodes, ways)
                    
                    if conflict_count > 1:
                        ctx['osm_conflict_info'] = "%d nearby features of this type in OSM." % conflict_count
                    elif conflict_count == 1:
                        ctx['osm_conflict_info'] = "1 nearby feature of this type in OSM."
                    elif conflict_count == 0:
                        ctx['osm_conflict_info'] = "No nearby features of this type in OSM."
                    else:
                        ctx['osm_conflict_info'] = "Error querying OSM."
                else:
                    ctx["osm_conflict_info"] = "Could not check for conflicting features - no OSM query set for this layer."
            else:
                ctx['osm_conflict_info'] = ""

            if form.cleaned_data['show_features_in_selection'] == 'yes':
                ctx['feature_selection_geometry'] = osm.feature_selection_geojson(workslice_features)
            elif form.cleaned_data['show_features_in_selection'] == 'centroids':
                ctx['feature_selection_geometry'] = osm.feature_selection_geojson(workslice_features, True)

    else:
        ctx['info'] = " ".join(form.errors['__all__'])
    # ctx['queries'] = django.db.connections[layer_in_dataset.dataset.name].queries

    return HttpResponse(json.dumps(ctx), content_type='application/json')
