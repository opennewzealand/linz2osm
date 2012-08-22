# Legal: http://djangosnippets.org/about/tos/
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
    Format some content using Pygments. Include line-numbers separated from the code.
    Usage: {{ content|stylize:"language" }}
    """
    lexer = get_lexer_by_name(style, encoding='UTF-8')
    return mark_safe(highlight(value, lexer, HtmlFormatter(linenos='table')))

@register.filter(name='stylize_no_ln')
@stringfilter
def stylize_no_ln(value, style):
    """ 
    Format some content using Pygments. No line numbers.
    Usage: {{ content|stylize:"language" }}
    """
    lexer = get_lexer_by_name(style, encoding='UTF-8')
    return mark_safe(highlight(value, lexer, HtmlFormatter(linenos=False)))

@register.filter(name='stylize_inline_ln')
@stringfilter
def stylize_inline_ln(value, style):
    """ 
    Format some content using Pygments. Inline line numbers.
    Usage: {{ content|stylize:"language" }}
    """
    lexer = get_lexer_by_name(style, encoding='UTF-8')
    return mark_safe(highlight(value, lexer, HtmlFormatter(linenos='inline')))
