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

import re

from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponse
from django.utils import simplejson
from django.template import RequestContext
from django import forms

from linz2osm.data_dict.models import Layer, Tag, Dataset, LayerInDataset
from linz2osm.utils.forms import BootstrapErrorList
from linz2osm.convert import osm

def tag_eval(request, object_id=None):
    if object_id:
        tag = get_object_or_404(Tag, pk=object_id)
        code = tag.code
    else:
        code = request.GET.get('code', '')
    
    fields = simplejson.loads(request.GET.get('fields', '{}'))
    
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
    return HttpResponse(simplejson.dumps(r), content_type='text/plain')

def layer_stats(request, object_id=None):
    # Because of breakage in django-admin, objectids come escaped
    object_id = re.sub("_5F", "_", object_id)
    
    l = get_object_or_404(Layer, name=object_id)
    
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

class PreviewForm(forms.Form):
    # From http://stackoverflow.com/a/4880869/186777
    def __init__(self, *args, **kwargs):
        datasets = kwargs.pop('datasets')
        super(PreviewForm, self).__init__(*args, **kwargs)
        self.fields['dataset'].queryset = datasets
    
    dataset = forms.ModelChoiceField(queryset=Dataset.objects.none(), required=True)
    starting_id = forms.IntegerField(min_value=0, required=False)

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
            starting_id = form.cleaned_data['starting_id'] or 0
            if layer.geometry_type == 'POINT':
                feature_count = 100
            else:
                feature_count = 10
            feature_ids = [fid for fid in range(starting_id, starting_id + feature_count)]
            ctx['preview_data'] = osm.export_custom(form.cleaned_data['dataset'], layer, feature_ids, '111222333444555666777888999')
    else:
        form = PreviewForm(error_class=BootstrapErrorList, datasets=datasets)
    ctx['form'] = form
    return render_to_response('data_dict/preview.html', ctx, context_instance=RequestContext(request))

