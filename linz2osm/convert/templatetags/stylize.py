# based on http://www.djangosnippets.org/snippets/350/

from django.template import Library, Node, resolve_variable
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

register = Library()

@register.filter(name='stylize')
@stringfilter
def stylize(value, style):
    """ 
    Format some content using Pygments.
    Usage: {{ content|stylize:"language" }}
    """
    lexer = get_lexer_by_name(style, encoding='UTF-8')
    return mark_safe(highlight(value, lexer, HtmlFormatter(linenos='table')))
