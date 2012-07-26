from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils import simplejson, text
from django.conf import settings
from django import forms

from linz2osm.data_dict.models import Layer, Dataset, LayerInDataset
from linz2osm.workslices.models import Workslice

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
        raise forms.ValidationError('Not implemented yet' % (data))
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

    if request.method == 'POST':
        form = WorksliceForm(request.POST, error_class=BootstrapErrorList)
        if form.is_valid():
            # well, bully for you
            pass
    else:
        form = WorksliceForm(error_class=BootstrapErrorList)
    ctx = {
        'layer_in_dataset': layer_in_dataset,
        'workslices': layer_in_dataset,
        'form': form,
        'title': "%s - %s" % (layer_in_dataset.dataset.description, layer_in_dataset.layer.name),
    }
    return render_to_response('workslices/create.html', ctx, context_instance=RequestContext(request))

