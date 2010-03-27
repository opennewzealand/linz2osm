import traceback

from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.utils import simplejson

from linz2osm.data_dict.models import Tag

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
