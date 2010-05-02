from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils import simplejson
from django.conf import settings
from django import forms

from linz2osm.data_dict.models import Layer
from linz2osm.convert import osm

DATASETS = dict([(k,v['_description']) for k,v in settings.DATABASES.items() if k != 'default'])

class BoundsForm(forms.Form):
    bounds = forms.RegexField(regex=r'((-?(\d+)(\.\d+)?),){3}(-?(\d+)(\.\d+)?)', required=False, help_text='minx,miny,maxx,maxy')
    
    def clean_bounds(self):
        b = self.cleaned_data['bounds']
        if not b:
            return None
        try:
            minx,miny,maxx,maxy = [float(c) for c in b.split(',')]
        except ValueError:
            raise forms.ValidationError("Invalid bounding box")
        if minx > maxx:
            raise forms.ValidationError("Invalid bounding box (minx > maxx)")
        if miny > maxy:
            raise forms.ValidationError("Invalid bounding box (miny > maxy)")
        if minx < -180 or minx > 180 or maxx < -180 or maxx > 180:
            raise forms.ValidationError("Invalid bounding box (minx/maxx out of bounds -180,+180)")
        if miny < -90 or miny > 90 or maxy < -90 or maxy > 90:
            raise forms.ValidationError("Invalid bounding box (miny/maxy out of bounds -90,+90)")
        return minx,miny,maxx,maxy

class ExportDataForm(BoundsForm):
    dataset = forms.ChoiceField(choices=[('', '---------')] + DATASETS.items())
    layer = forms.ModelChoiceField(Layer.objects.order_by('name'))
    
    def __init__(self, dataset_layers, *args, **kwargs):
        self.dataset_layers = dataset_layers
        super(ExportDataForm, self).__init__(*args, **kwargs)
    
    def clean(self):
        fcd = self.cleaned_data
        if fcd['layer'] and fcd['dataset']:
            if fcd['layer'].name not in self.dataset_layers[fcd['dataset']]:
                raise forms.ValidationError("Layer %s is not available in Dataset %s" % (fcd['layer'], DATASETS[fcd['dataset']]))
        return fcd

def layer_data(request):
    dataset_layers = {}
    all_layers = set(Layer.objects.values_list('name', flat=True))
    for ds in DATASETS.keys():
        ds_tables = set(osm.dataset_tables(ds))
        ds_layers = list(all_layers.intersection(ds_tables))
        ds_layers.sort()
        dataset_layers[ds] = ds_layers 
    
    if request.method == "POST":
        form = ExportDataForm(dataset_layers, request.POST)
        if form.is_valid():
            return layer_data_export(request, form.cleaned_data['dataset'], form.cleaned_data['layer'].name)
    else:
        form = ExportDataForm(dataset_layers)
        
    ctx = {
        'form': form,
        'title': 'Export Layer Data',
        'dataset_layers': simplejson.dumps(dataset_layers),
    }
    return render_to_response('convert/layer_data.html', ctx, context_instance=RequestContext(request))

def layer_data_export(request, dataset_id, layer_name):
    if not dataset_id in DATASETS:
        raise Http404('Dataset %s not found' % dataset_id)

    layer = get_object_or_404(Layer, pk=layer_name)
    if not osm.has_layer(dataset_id, layer):
        raise Http404('Layer %s not available in dataset %s' % (layer_name, DATASETS[dataset_id]))
    
    ctx = {
        'dataset_id': dataset_id,
        'dataset_name': DATASETS[dataset_id],
        'layer': layer,
        'title': 'Export %s from %s' % (str(layer), DATASETS[dataset_id]),
    }
    if request.method == "POST":
        form = BoundsForm(request.REQUEST)
        if form.is_valid():
            try:
                data = osm.export(dataset_id, layer, form.cleaned_data['bounds'])
            except osm.Error, e:
                ctx['error'] = str(e)
            else:
                if 'preview' in request.REQUEST:
                    ctx['preview_content'] = data
                else:
                    response = HttpResponse(data, content_type='text/xml')
                    response['Content-Disposition'] = 'attachment; filename=%s.osm' % layer_name
                    return response
    else:
        form = BoundsForm()
        
    ctx['form'] = form
    return render_to_response('convert/layer_data_export.html', ctx, context_instance=RequestContext(request))
