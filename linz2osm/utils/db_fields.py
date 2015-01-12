# Legal: http://djangosnippets.org/about/tos/

"""
JSONField modified from: http://djangosnippets.org/snippets/377/ and http://www.djangosnippets.org/snippets/1478/
"""

import datetime
import json
import re
import warnings

from django import forms
from django.conf import settings
from django.db import models


def register_south_field(field_class):
    # make the fields work in South
    from south.modelsinspector import add_introspection_rules
    module = field_class.__module__
    regex = r'^%s\.%s' % (re.escape(module), field_class.__name__)

    add_introspection_rules([], [regex])
    return field_class


class JSONWidget(forms.Textarea):
    def render(self, name, value, attrs=None):
        if not isinstance(value, basestring):
            value = json.dumps(value, indent=2)
        return super(JSONWidget, self).render(name, value, attrs)

class JSONFormField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = JSONWidget
        super(JSONFormField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value: return
        try:
            return json.loads(value, encoding=settings.DEFAULT_CHARSET)
        except Exception, exc:
            raise forms.ValidationError(u'JSON decode error: %s' % (unicode(exc),))

class JSONDateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, datetime.time):
            return obj.strftime('%H:%M:%S')
        return json.JSONEncoder.default(self, obj)

# class JSONField(models.TextField):
#     description = _("Data that serializes and deserializes into and out of JSON.")

#     def pre_save(self, model_instance, add):
#         value = getattr(model_instance, self.attname, None)
#         return self._dumps(value)


# Based on http://www.djangosnippets.org/snippets/1478/
@register_south_field
class JSONField(models.TextField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly
    """

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def formfield(self, form_class=JSONFormField, **kwargs):
        return super(JSONField, self).formfield(form_class=form_class, **kwargs)

    def db_type(self):
        return 'text'

    def to_python(self, value):
        """
        Convert our string value to JSON after we load it from the DB
        """
        if value == "":
            return None

        if isinstance(value, basestring):
            try:
                return json.loads(value)
            except ValueError as e:
                raise ValueError("Error loading JSON %s (%s)" % (value, e.message))

        return value

    def get_prep_value(self, value):
        """
        Perform preliminary non-db specific value checks and conversions.

        Used by the default implementations of ``get_db_prep_save``and
        `get_db_prep_lookup```
        """

        value = json.dumps(value, sort_keys=True)

        return super(JSONField, self).get_prep_value(value)

    def get_db_prep_save(self, value, *args, **kwargs):
        """
        Convert our JSON object to a string before we save
        """
        if value in (None, ""):
            if self.null:
                return None
            else:
                return ''

        return super(JSONField, self).get_db_prep_save(value, *args, **kwargs)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        if value:
            return json.dumps(value, sort_keys=True)
        else:
            return ""

    def contribute_to_class(self, cls, name):
        super(JSONField, self).contribute_to_class(cls, name)

        def get_json(model_instance):
            warnings.warn("Use model.field instead of model.get_field_json()", DeprecationWarning)
            return getattr(model_instance, self.attname)
        setattr(cls, 'get_%s_json' % self.name, get_json)

        def set_json(model_instance, json):
            warnings.warn("Use model.field instead of model.set_field_json()", DeprecationWarning)
            return setattr(model_instance, self.attname, json)
        setattr(cls, 'set_%s_json' % self.name, set_json)

    def get_default(self):
        """
        Returns the default value for this field. For a JSONField the default value
        should be an Object, not an encoded JSON string.
        """
        if self.has_default():
            if callable(self.default):
                return self.default()
            return self.default  # is an object already
        if (not self.empty_strings_allowed or self.null):
            return None
        return ""

    def post_init(self, **kwargs):
        if 'sender' in kwargs and 'instance' in kwargs:
            if kwargs['sender'] == self.class_name and hasattr(kwargs['instance'], self.attname):
                value = self.value_from_object(kwargs['instance'])
                if (value):
                    setattr(kwargs['instance'], self.attname, self._loads(value))
                else:
                    setattr(kwargs['instance'], self.attname, None)