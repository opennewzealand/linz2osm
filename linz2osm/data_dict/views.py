import re

from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponse
from django.utils import simplejson
from django.template import RequestContext

from linz2osm.data_dict.models import Layer, Tag, Dataset, LayerInDataset

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
    # FIXME: Why? 
    # object_id = re.sub("_5F", "_", object_id)
    
    l = get_object_or_404(Layer, name=object_id)
    
    c = {
        'layer': l,
        'statistics': l.get_statistics(),
        'title': '%s Statistics' % l,
    }
    
    return render_to_response('data_dict/layer_stats.html', c, context_instance=RequestContext(request))

def show_dataset(request, dataset_id=None):
    dataset = get_object_or_404(Dataset, name=dataset_id)
    ctx = {
        'dataset': dataset,
        'layers_in_dataset': dataset.layerindataset_set.order_by('layer__name').all(),
        'title': dataset.description,
        }
    return render_to_response('data_dict/show_dataset.html', ctx, context_instance=RequestContext(request))
        

