from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import make_safe

register = template.Library()

# @register.filter
# @stringfilter
# def linked_as(value, arg):
#     return make_safe("<a href='%s'>%s</a>" % (value, arg))
