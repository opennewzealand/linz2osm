from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.utils import simplejson
from django.conf import settings
from django import forms

from linz2osm.data_dict.models import Layer, Tag
from linz2osm.convert import osm

class LayerDataForm(forms.Form):
    DATASET_CHOICES = [(k,v['_description']) for k,v in settings.DATABASES.items() if k != 'default']
    
    dataset = forms.ChoiceField(choices=DATASET_CHOICES)
    layer = forms.ModelChoiceField(Layer.objects.all())
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
    
def layer_data(request):
    if request.method == "POST":
        form = LayerDataForm(request.POST)
        if form.is_valid():
            data = osm.export(form.cleaned_data['dataset'], form.cleaned_data['layer'], form.cleaned_data['bounds']) 
            response = HttpResponse(data, content_type='text/xml')
            #response['Content-Disposition'] = 'attachment; filename=%s.xml' % form.cleaned_data['layer'].name
            return response 
    else:
        form = LayerDataForm()
        
    return render_to_response('convert/layer_data.html', {'form':form, 'title':'Convert Layer Data'}, context_instance=RequestContext(request))
