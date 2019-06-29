import copy

from django import forms
from django.db import models
from django.core.exceptions import ValidationError, ImproperlyConfigured
from djangae.forms.fields import ListFormField
from django.utils.text import capfirst


class _FakeModel(object):
    """
    An object of this class can pass itself off as a model instance
    when used as an arguments to Field.pre_save method (item_fields
    of iterable fields are not actually fields of any model).
    """

    def __init__(self, field, value):
        setattr(self, field.attname, value)


class IterableField(models.Field):
    @property
    def _iterable_type(self): raise NotImplementedError()

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def db_type(self, connection):
        return 'list'

    def get_prep_lookup(self, lookup_type, value):
        if hasattr(value, 'prepare'):
            return value.prepare()
        if hasattr(value, '_prepare'):
            return value._prepare()

        if value is None:
            raise ValueError("You can't query an iterable field with None")

        if lookup_type == 'isnull' and value in (True, False):
            return value

        if lookup_type not in ['exact', 'in', 'regex', 'iregex']:
            raise ValueError("You can only query using exact and in lookups on iterable fields")

        if isinstance(value, (list, set)):
            return [ self.item_field_type.to_python(x) for x in value ]

        return self.item_field_type.to_python(value)

    def get_prep_value(self, value):
        if value is None:
            raise ValueError("You can't set a {} to None (did you mean {}?)".format(
                self.__class__.__name__, str(self._iterable_type())
            ))

        if isinstance(value, basestring):
            # Catch accidentally assigning a string to a ListField
            raise ValueError("Tried to assign a string to a {}".format(self.__class__.__name__))

        return super(IterableField, self).get_prep_value(value)

    def __init__(self, item_field_type, *args, **kwargs):

        # This seems bonkers, we shout at people for specifying null=True, but then do it ourselves. But this is because
        # *we* abuse None values for our own purposes (to represent an empty iterable) if someone else tries to then
        # all hell breaks loose
        if kwargs.get("null", False):
            raise RuntimeError("IterableFields cannot be set as nullable (as the datastore doesn't differentiate None vs []")

        kwargs["null"] = True

        default = kwargs.get("default", [])

        self._original_item_field_type = copy.deepcopy(item_field_type) # For deconstruction purposes

        if default is not None and not callable(default):
            kwargs["default"] = lambda: self._iterable_type(default)

        if hasattr(item_field_type, 'attname'):
            item_field_type = item_field_type.__class__

        if callable(item_field_type):
            item_field_type = item_field_type()

        if isinstance(item_field_type, models.ForeignKey):
            raise ImproperlyConfigured("Lists of ForeignKeys aren't supported, use RelatedSetField instead")

        self.item_field_type = item_field_type

        # We'll be pretending that item_field is a field of a model
        # with just one "value" field.
        assert not hasattr(self.item_field_type, 'attname')
        self.item_field_type.set_attributes_from_name('value')

        super(IterableField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(IterableField, self).deconstruct()
        args = (self._original_item_field_type,)
        del kwargs["null"]
        return name, path, args, kwargs

    def contribute_to_class(self, cls, name):
        self.item_field_type.model = cls
        self.item_field_type.name = name
        super(IterableField, self).contribute_to_class(cls, name)

    def _map(self, function, iterable, *args, **kwargs):
        return self._iterable_type(function(element, *args, **kwargs) for element in iterable)

    def to_python(self, value):
        if value is None:
            return self._iterable_type([])

        # If possible, parse the string into the iterable
        if not hasattr(value, "__iter__"): # Allows list/set, not string
            if isinstance(value, basestring):
                if (self._iterable_type == set and value.startswith("{") and value.endswith("}")) or \
                   (self._iterable_type == list and value.startswith("[") and value.endswith("]")):
                    value = [x.strip() for x in value[1:-1].split(",") ]
                else:
                    raise ValueError("Unable to parse string into iterable field")
            else:
                raise TypeError("Tried to assign non-iterable to an IterableField")

        return self._map(self.item_field_type.to_python, value)

    def pre_save(self, model_instance, add):
        """
            Gets our value from the model_instance and passes its items
            through item_field's pre_save (using a fake model instance).
        """
        value = getattr(model_instance, self.attname)
        if value is None:
            return None

        return self._map(lambda item: self.item_field_type.pre_save(_FakeModel(self.item_field_type, item), add), value)

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
            if value is None:
                return None

        # If the value is an empty iterable, store None
        if value == self._iterable_type([]):
            return None

        return self._map(self.item_field_type.get_db_prep_save, value,
                         connection=connection)


    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        """
        Passes the value through get_db_prep_lookup of item_field.
        """
        return self.item_field_type.get_db_prep_lookup(
            lookup_type, value, connection=connection, prepared=prepared)

    def validate(self, value_list, model_instance):
        """ We want to override the default validate method from django.db.fields.Field, because it
            is only designed to deal with a single choice from the user.
        """
        if not self.editable:
            # Skip validation for non-editable fields
            return

        # Validate choices
        if self.choices:
            valid_values = []
            for choice in self.choices:
                if isinstance(choice[0], (list, tuple)):
                    # this is an optgroup, so look inside it for the options
                    for optgroup_choice in choice[0]:
                        valid_values.append(optgroup_choice[0])
                else:
                    valid_values.append(choice[0])
            for value in value_list:
                if value not in valid_values:
                    # TODO: if there is more than 1 invalid value then this should show all of the invalid values
                    raise ValidationError(self.error_messages['invalid_choice'] % value)
        # Validate null-ness
        if value_list is None and not self.null:
            raise ValidationError(self.error_messages['null'])

        if not self.blank and not value_list:
            raise ValidationError(self.error_messages['blank'])

        # apply the default items validation rules
        for value in value_list:
            self.item_field_type.clean(value, model_instance)

    def formfield(self, **kwargs):
        """ If this field has choices, then we can use a multiple choice field.
            NB: The choices must be set on *this* field, e.g. this_field = ListField(CharField(), choices=x)
            as opposed to: this_field = ListField(CharField(choices=x))
        """
        #Largely lifted straight from Field.formfield() in django.models.__init__.py
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        if self.has_default(): #No idea what this does
            if callable(self.default):
                defaults['initial'] = self.default
                defaults['show_hidden_initial'] = True
            else:
                defaults['initial'] = self.get_default()

        if self.choices:
            form_field_class = forms.MultipleChoiceField
            defaults['choices'] = self.get_choices(include_blank=False) #no empty value on a multi-select
        else:
            form_field_class = ListFormField
        defaults.update(**kwargs)
        return form_field_class(**defaults)


class ListField(IterableField):
    def __init__(self, *args, **kwargs):
        self.ordering = kwargs.pop('ordering', None)
        if self.ordering is not None and not callable(self.ordering):
            raise TypeError("'ordering' has to be a callable or None, "
                            "not of type %r." % type(self.ordering))
        super(ListField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "ListField"

    def pre_save(self, model_instance, add):
        value = super(ListField, self).pre_save(model_instance, add)

        if value and self.ordering:
            value.sort(key=self.ordering)

        return value

    @property
    def _iterable_type(self):
        return list

    def deconstruct(self):
        name, path, args, kwargs = super(ListField, self).deconstruct()
        kwargs['ordering'] = self.ordering
        return name, path, args, kwargs

class SetField(IterableField):
    @property
    def _iterable_type(self):
        return set

    def get_internal_type(self):
        return "SetField"

    def db_type(self, connection):
        return 'set'

    def get_db_prep_save(self, *args, **kwargs):
        ret = super(SetField, self).get_db_prep_save(*args, **kwargs)
        if ret:
            ret = list(ret)
        return ret

    def get_db_prep_lookup(self, *args, **kwargs):
        ret =  super(SetField, self).get_db_prep_lookup(*args, **kwargs)
        if ret:
            ret = list(ret)
        return ret

    def value_to_string(self, obj):
        """
        Custom method for serialization, as JSON doesn't support
        serializing sets.
        """
        return str(list(self._get_val_from_obj(obj)))
