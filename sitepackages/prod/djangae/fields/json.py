"""
JSONField automatically serializes most Python terms to JSON data.
Creates a TEXT field with a default value of "{}".  See test_json.py for
more information.

 from django.db import models
 from django_extensions.db.fields import json

 class LOL(models.Model):
     extra = json.JSONField()

This field originated from the django_extensions project: https://github.com/django-extensions/django-extensions
"""

from __future__ import absolute_import

import json
from collections import OrderedDict

from django.db import models
from django.conf import settings
from django.utils import six
from django.core.serializers.json import DjangoJSONEncoder

from djangae.forms.fields import JSONFormField, JSONWidget

__all__ = ( 'JSONField',)


def dumps(value):
    return DjangoJSONEncoder().encode(value)


def loads(txt, object_pairs_hook=None):
    value = json.loads(
        txt,
        encoding=settings.DEFAULT_CHARSET,
        object_pairs_hook=object_pairs_hook,
    )
    return value


class JSONDict(dict):
    """
    Hack so repr() called by dumpdata will output JSON instead of
    Python formatted data.  This way fixtures will work!
    """
    def __repr__(self):
        return dumps(self)


class JSONUnicode(six.text_type):
    """
    As above
    """
    def __repr__(self):
        return dumps(self)


class JSONList(list):
    """
    As above
    """
    def __repr__(self):
        return dumps(self)


class JSONOrderedDict(OrderedDict):
    """
    As above
    """
    def __repr__(self):
        return dumps(self)


class JSONField(models.TextField):
    """JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.  Main thingy must be a dict object."""

    def __init__(self, use_ordered_dict=False, *args, **kwargs):
        if 'default' in kwargs:
            if not callable(kwargs['default']):
                raise TypeError("'default' must be a callable (e.g. 'dict' or 'list')")
        else:
            kwargs['default'] = dict

        # use `collections.OrderedDict` rather than built-in `dict`
        self.use_ordered_dict = use_ordered_dict

        models.TextField.__init__(self, *args, **kwargs)

    def parse_json(self, value):
        """Convert our string value to JSON after we load it from the DB"""
        if value is None or value == '':
            return {}
        elif isinstance(value, six.string_types):
            if self.use_ordered_dict:
                res = loads(value, object_pairs_hook=OrderedDict)
            else:
                res = loads(value)
            if isinstance(res, OrderedDict) and self.use_ordered_dict:
                return JSONOrderedDict(res)
            elif isinstance(res, dict):
                return JSONDict(**res)
            elif isinstance(res, six.string_types):
                return JSONUnicode(res)
            elif isinstance(res, list):
                return JSONList(res)
            return res
        else:
            return value

    def to_python(self, value):
        return self.parse_json(value)

    def from_db_value(self, value, expression, connection, context):
        return self.parse_json(value)

    def get_db_prep_save(self, value, connection, **kwargs):
        """Convert our JSON object to a string before we save"""
        if value is None and self.null:
            return None
        return super(JSONField, self).get_db_prep_save(dumps(value), connection=connection)

    def south_field_triple(self):
        """Returns a suitable description of this field for South."""
        # We'll just introspect the _actual_ field.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.TextField"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(JSONField, self).deconstruct()
        if self.default == {}:
            del kwargs['default']
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {
            'form_class': JSONFormField,
            'widget': JSONWidget,
        }
        defaults.update(kwargs)
        return super(JSONField, self).formfield(**defaults)
