from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils import simplejson, text
from django.conf import settings
from django import forms

from linz2osm.data_dict.models import Layer, Dataset
from linz2osm.convert import osm
from linz2osm.workslices.models import Workslice

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
    dataset = forms.ModelChoiceField(Dataset.objects.order_by('name'))
    layer = forms.ModelChoiceField(Layer.objects.order_by('name'))
    
    def __init__(self, dataset_layers, *args, **kwargs):
        self.dataset_layers = dataset_layers
        super(ExportDataForm, self).__init__(*args, **kwargs)
    
    def clean(self):
        fcd = self.cleaned_data
        
        if ('layer' in fcd) and ('dataset' in fcd):
            if fcd['layer'].name not in self.dataset_layers[fcd['dataset'].name]:
                raise forms.ValidationError("Layer %s is not available in Dataset %s" % (fcd['layer'], Dataset.objects.get(name=fcd['dataset'].name)))
        return fcd

def layer_data(request):
    dataset_layers = {}
    all_layers = set(Layer.objects.values_list('name', flat=True))
    for ds in Dataset.objects.all():
        ds_tables = set(osm.dataset_tables(ds.name))
        ds_layers = list(all_layers.intersection(ds_tables))
        ds_layers.sort()
        dataset_layers[ds.name] = ds_layers 
    
    if request.method == "POST":
        form = ExportDataForm(dataset_layers, request.POST)
        if form.is_valid():
            return layer_data_export(request, form.cleaned_data['dataset'].name, form.cleaned_data['layer'].name)
    else:
        form = ExportDataForm(dataset_layers)
        
    ctx = {
        'form': form,
        'title': 'Export Layer Data',
        'dataset_layers': simplejson.dumps(dataset_layers),
    }
    return render_to_response('convert/layer_data.html', ctx, context_instance=RequestContext(request))

def layer_data_export(request, dataset_id, layer_name):
    dataset = get_object_or_404(Dataset, name=dataset_id)
    layer = get_object_or_404(Layer, pk=layer_name)
    if not osm.has_layer(dataset.name, layer):
        raise Http404('Layer %s not available in dataset %s' % (layer_name, dataset))
    
    ctx = {
        'dataset_id': dataset.name,
        'dataset_description': dataset.description,
        'layer': layer,
        'title': 'Export %s from %s' % (str(layer), dataset),
    }
    if request.method == "POST":
        form = BoundsForm(request.REQUEST)
        if form.is_valid():
            if 'checkout' in request.REQUEST:
                try:
                    workslice = Workslice.objects.create_workslice(layer, dataset_id, form.cleaned_data['bounds'], request.user)
                except osm.Error, e:
                    ctx['error'] = str(e)
                else:
                    response = HttpResponse()
                    response.status_code = 303
                    response['Location'] = workslice.get_absolute_url()
                # response['Location'] = "%s%s.osc" % (settings.MEDIA_URL, workslice.name)
                    return response
            else:
                try:
                    feature_limit = None
                    if 'preview' in request.REQUEST:
                        feature_limit = 50
                    data = osm.export(dataset_id, layer, form.cleaned_data['bounds'], feature_limit)
                except osm.Error, e:
                    ctx['error'] = str(e)
                else:
                    if 'preview' in request.REQUEST:
                        ctx['preview_content'] = data
                    else:
                        # download
                        filename = "%s.osc" % layer_name
                        if 'download_gz' in request.REQUEST:
                            data = text.compress_string(data)
                            filename += ".gz"
                            content_type = 'application/x-gzip'
                        else:
                            content_type = 'text/xml'
                        response = HttpResponse(data, content_type=content_type)
                        response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    
                        if content_type == 'application/x-gzip':
                             response['Content-Encoding'] = ''
                    
                        return response
    else:
        form = BoundsForm()
        
    ctx['form'] = form
    return render_to_response('convert/layer_data_export.html', ctx, context_instance=RequestContext(request))
