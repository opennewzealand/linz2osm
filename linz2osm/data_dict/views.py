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

import json
import re

from itertools import chain
from datetime import datetime as dt

from django.core import serializers
from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponse
from django.template import RequestContext
from django import forms
from django.contrib.auth.decorators import login_required, user_passes_test

from linz2osm.data_dict.models import *
from linz2osm.data_dict import tasks
from linz2osm.utils.forms import BootstrapErrorList
from linz2osm.convert import osm

def tag_eval(request, object_id=None):
    if object_id:
        tag = get_object_or_404(Tag, pk=object_id)
        code = tag.code
    else:
        code = request.GET.get('code', '')

    fields = json.loads(request.GET.get('fields', '{}'))

    try:
        value = Tag.objects.eval(code, fields)
    except Tag.ScriptError, e:
        r = {
            'status': 'error',
            'error': "ScriptError: " + str(e),
        }
    else:
        r = {
            'status': 'ok',
            'fields': fields,
            'value': value,
        }
    return HttpResponse(json.dumps(r), content_type='text/plain')

def layer_stats(request, layer_id=None):
    # Because of interesting things in django-admin, objectids come escaped
    layer_id = re.sub("_5F", "_", layer_id)

    l = get_object_or_404(Layer, name=layer_id)

    c = {
        'layer': l,
        'statistics': l.get_statistics(),
        'title': '%s Statistics' % l,
    }

    return render_to_response('data_dict/layer_stats.html', c, context_instance=RequestContext(request))

def field_stats(request, dataset_id=None, layer_id=None, field_name=None):
    dataset = get_object_or_404(Dataset, name=dataset_id)
    layer = get_object_or_404(Layer, name=layer_id)
    layer_in_dataset = get_object_or_404(dataset.layerindataset_set, layer=layer)

    ctx = {
        'dataset': dataset,
        'layer': layer,
        'layer_in_dataset': layer_in_dataset,
        'title': "%s/%s/%s Statistics" % (dataset.name, layer.name, field_name),
        'statistics': layer_in_dataset.get_statistics_for(field_name),
        'field_name': field_name,
        }
    return render_to_response('data_dict/field_stats.html', ctx, context_instance=RequestContext(request))

def show_dataset(request, dataset_id=None):
    dataset = get_object_or_404(Dataset, name=dataset_id)
    ctx = {
        'dataset': dataset,
        'layers_in_dataset': dataset.layerindataset_set.order_by('layer__name').all(),
        'title': dataset.description,
        }
    return render_to_response('data_dict/show_dataset.html', ctx, context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda u: u.has_perm(u'data_dict.change_dataset'))
def merge_deletions_from_dataset(request, dataset_id=None):
    dataset = get_object_or_404(Dataset, name=dataset_id)
    ctx = {
        'dataset': dataset,
        'show_button': True,
        'layers_in_dataset': dataset.layerindataset_set.order_by('layer').all(),
        }

    if dataset.generating_deletions_osm:
        ctx['show_button'] = False
    elif request.method == 'POST':
        ctx['show_button'] = False
        dataset.generating_deletions_osm = True
        dataset.layerindataset_set.update(last_deletions_dump_filename='')
        tasks.deletions_export.delay(dataset)
        dataset.save()
    return render_to_response('data_dict/merge_deletions_for_dataset.html', ctx, context_instance=RequestContext(request))

class UpdateForm(forms.Form):
    update_version = forms.DateField(input_formats=['%Y-%m-%d'])

    def __init__(self, *args, **kwargs):
        self.dataset = kwargs.pop('dataset')
        self.max_update_version = self.dataset.get_max_update_version()
        super(UpdateForm, self).__init__(*args, **kwargs)

    def clean_update_version(self):
        cleaned_update_version_str = self.cleaned_data['update_version'].strftime("%Y-%m-%d")

        if cleaned_update_version_str > self.max_update_version:
            raise forms.ValidationError("Update version cannot be after %s" % self.max_update_version)
        return cleaned_update_version_str

@login_required
@user_passes_test(lambda u: u.has_perm(u'data_dict.change_dataset'))
def update_dataset(request, dataset_id=None):
    # FIXME: pause workslice processing during update

    dataset = get_object_or_404(Dataset, name=dataset_id)
    max_update_version = dataset.get_max_update_version()
    last_update = dataset.get_last_update()
    ctx = {
        'dataset': dataset,
        'title': dataset.description,
        'update_version': max_update_version,
        'show_form': True,
        }

    if last_update and not last_update.complete and not last_update.error:
        ctx['show_form'] = False
        ctx['status'] = "Currently updating to %s" % last_update.to_version
        form = None
    else:
        if last_update and not last_update.complete and last_update.error:
            ctx['status'] = "Last update attempt ended with error: \n%s" % last_update.error
        if request.method == 'POST':
            form = UpdateForm(request.POST, error_class=BootstrapErrorList, dataset=dataset)
            if form.is_valid():
                update_version = form.cleaned_data['update_version']
                dataset_update = DatasetUpdate(
                    dataset=dataset,
                    from_version=dataset.version,
                    to_version=update_version,
                    seq=dataset.get_last_update_seq_no() + 1,
                    owner=request.user,
                    complete=False)
                tasks.dataset_update.delay(dataset_update)
                dataset_update.save()
                ctx['show_form'] = False
                ctx['status'] = "Currently updating to %s" % dataset_update.to_version
        else:
            form = UpdateForm(error_class=BootstrapErrorList, dataset=dataset, initial={'update_version': max_update_version})

    ctx['layers_in_dataset'] = dataset.layerindataset_set.order_by('layer__name').all()
    ctx['form'] = form

    return render_to_response('data_dict/update_dataset.html', ctx, context_instance=RequestContext(request))

class PreviewForm(forms.Form):
    # From http://stackoverflow.com/a/4880869/186777
    def __init__(self, *args, **kwargs):
        datasets = kwargs.pop('datasets')
        super(PreviewForm, self).__init__(*args, **kwargs)
        self.fields['dataset'].queryset = datasets

    dataset = forms.ModelChoiceField(queryset=Dataset.objects.none(), required=True)
    feature_limit = forms.IntegerField(min_value=0, max_value=100, required=False, initial=10)
    starting_id = forms.IntegerField(min_value=1, required=False, label='Starting feature ID')

def preview(request, layer_id=None):
    layer_id = re.sub("_5F", "_", layer_id)
    layer = get_object_or_404(Layer, pk=layer_id)
    datasets = layer.datasets.order_by('description').all()

    ctx = {
        'layer': layer,
        }

    if request.method == 'POST':
        form = PreviewForm(request.POST, error_class=BootstrapErrorList, datasets=datasets)
        if form.is_valid():
            starting_id = form.cleaned_data['starting_id'] or 1
            if form.cleaned_data['feature_limit']:
                feature_count = form.cleaned_data['feature_limit']
            elif layer.geometry_type == 'POINT':
                feature_count = 100
            else:
                feature_count = 10

            layer_in_dataset = LayerInDataset.objects.get(layer=layer, dataset=form.cleaned_data['dataset'])
            feature_ids = osm.get_base_and_limit_feature_ids(layer_in_dataset, starting_id, feature_count)

            try:
                ctx['preview_data'] = osm.export_custom(layer_in_dataset, feature_ids, '123_sample_workslice_id_123')
            except osm.Error, e:
                form._errors["__all__"] = form.error_class([unicode(e)])
    else:
        form = PreviewForm(error_class=BootstrapErrorList, datasets=datasets)
    ctx['form'] = form
    return render_to_response('data_dict/preview.html', ctx, context_instance=RequestContext(request))

def show_tagging(request, layer_id=None):
    layer_id = re.sub("_5F", "_", layer_id)
    layer = get_object_or_404(Layer, pk=layer_id)
    grouped_tags = layer.potential_tags()

    ctx = {
        'layer': layer,
        'grouped_tags': grouped_tags,
        }

    return render_to_response('data_dict/show_tagging.html', ctx, context_instance=RequestContext(request))

def layer_notes(request, layer_id=None):
    layer_id = re.sub("_5F", "_", layer_id)
    layer = get_object_or_404(Layer, pk=layer_id)

    ctx = {
        'layer': layer,
        }

    return render_to_response('data_dict/layer_notes.html', ctx, context_instance=RequestContext(request))

def export_data_dict(request):
    response = HttpResponse(
        serializers.serialize(
            "xml", chain(
                Group.objects.order_by('name').all(),
                Layer.objects.order_by('name').all(),
                Tag.objects.order_by('layer', 'tag').all(),
                Member.objects.order_by('relation_layer', 'member_layer', 'role').all()),
            indent=4,
            content_type='application/xml'))
    response['Content-Type'] = "application/xml"
    response['Content-Disposition'] = "attachment; filename=linz2osm-data_dict-export-%s.xml" % (dt.strftime(dt.now(), "%F-%H-%M-%S"),)
    return response

def list_layers(request):
    ctx = {
        'layers': Layer.objects.order_by('name').all(),
        }
    return render_to_response('data_dict/list_layers.html', ctx, context_instance=RequestContext(request))
