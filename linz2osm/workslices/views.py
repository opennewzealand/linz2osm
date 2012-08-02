import re
import json

from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils import simplejson, text
from django.conf import settings
from django.contrib.gis.geos import MultiPolygon, Polygon
from django import forms

from linz2osm.data_dict.models import Layer, Dataset, LayerInDataset
from linz2osm.workslices.models import Workslice, Cell, WorksliceTooFeaturefulError, FEATURE_LIMIT
from linz2osm.convert import osm

class BootstrapErrorList(forms.util.ErrorList):
    def __unicode__(self):
        return self.as_divs()
    def as_divs(self):
        if not self: return ''
        return u'<div class="errorlist">%s</div>' % ''.join([
                u'<div class="alert alert-error">%s</div>' % e for e in self])

class WorksliceForm(forms.Form):
    cells = forms.CharField(widget=forms.HiddenInput(), required=False)
    
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

def create_workslice(request, layer_in_dataset_id):
    layer_in_dataset = get_object_or_404(LayerInDataset, pk=layer_in_dataset_id)

    ctx = {
        'layer_in_dataset': layer_in_dataset,
        'workslices': layer_in_dataset,
        'title': "%s - %s" % (layer_in_dataset.dataset.description, layer_in_dataset.layer.name),
    }
    if request.method == 'POST':
        form = WorksliceForm(request.POST, error_class=BootstrapErrorList)
        if form.is_valid():
            try:
                workslice = Workslice.objects.create_workslice(layer_in_dataset, request.user, form.extent)
            except osm.Error, e:
                ctx['error'] = str(e)
            except WorksliceTooFeaturefulError, e:
                form._errors["__all__"] = form.error_class([u"Too many features in selection (over %d): Please reduce selection" % FEATURE_LIMIT])
            else:
                response = HttpResponse()
                response.status_code = 303
                response['Location'] = workslice.get_absolute_url()
                return response
            pass
    else:
        form = WorksliceForm(error_class=BootstrapErrorList)
    ctx['form'] = form
    return render_to_response('workslices/create.html', ctx, context_instance=RequestContext(request))

def workslice_info(request, layer_in_dataset_id):
    layer_in_dataset = get_object_or_404(LayerInDataset, pk=layer_in_dataset_id)

    ctx = {}
    
    form = WorksliceForm(request.POST, error_class=BootstrapErrorList)
    if form.is_valid():
        feature_count = osm.get_layer_feature_count(layer_in_dataset.dataset.name, layer_in_dataset.layer, form.extent)
        # feature_count = len(osm.get_layer_feature_ids(layer_in_dataset, form.extent))
        if feature_count > FEATURE_LIMIT:
            ctx['info'] = "Too many features (over %d): please reduce selection." % FEATURE_LIMIT
        elif feature_count > 1:
            ctx['info'] = "%d features in selection." % feature_count
        elif feature_count > 0:
            ctx['info'] = "One feature in selection."
        elif feature_count == 0:
            ctx['info'] = "No features in selection. (%d cells: form extent is %s)" % (form.num_cells, form.extent.wkt)
        else:
            ctx['info'] = "Serious error calculating features."
    else:
        ctx['info'] = " ".join(form.errors['__all__'])

    return HttpResponse(json.dumps(ctx), content_type='application/json')
