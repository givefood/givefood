import django
from django import forms
from django.db import router, models
from django.db.models.query import QuerySet
from django.db.models.fields.related import ForeignObject, ForeignObjectRel
from django.utils.functional import cached_property
from django.core.exceptions import ImproperlyConfigured, ValidationError
from djangae.forms.fields import (
    encode_pk,
    GenericRelationFormfield
)
from django.utils import six

class RelatedIteratorRel(ForeignObjectRel):
    def __init__(self, field, to, related_name=None, limit_choices_to=None, on_delete=models.DO_NOTHING):
        self.field = field
        if django.VERSION[1] < 9: # Django 1.8 compatibility
            self.to = to
        self.model = to
        self.related_name = related_name
        self.related_query_name = None
        self.field_name = None
        self.parent_link = None
        self.on_delete = on_delete
        self.symmetrical = False

        if limit_choices_to is None:
            limit_choices_to = {}
        self.limit_choices_to = limit_choices_to
        self.multiple = True

    def is_hidden(self):
        "Should the related object be hidden?"
        return self.related_name and self.related_name[-1] == '+'

    def set_field_name(self):
        self.field_name = self.field_name or self.to._meta.pk.name

    def get_related_field(self):
        """
        Returns the field in the to' object to which this relationship is tied
        (this is always the primary key on the target model). Provided for
        symmetry with ManyToOneRel.
        """
        return self.to._meta.pk


class OrderedQuerySet(QuerySet):

    def _fetch_all(self):
        """
            Fetch all uses the standard iterator but sorts the values on the
            way out, this maintains the lazy evaluation of querysets
        """
        if self._result_cache is None:
            results = list(self.iterator())
            ordered_results = []
            pk_hash = {x.pk: x for x in results}
            for pk in self.ordered_pks:
                obj = pk_hash.get(pk)
                if obj:
                    ordered_results.append(obj)
            self._result_cache = ordered_results
        if self._prefetch_related_lookups and not self._prefetch_done:
            self._prefetch_related_objects()

    def _clone(self, *args, **kwargs):
        """
            We need to attach the ordered_pk list on the clone to it continues
            through the chain
        """
        c = super(OrderedQuerySet, self)._clone(*args, **kwargs)
        c.ordered_pks = self.ordered_pks[:]
        return c

    def __getitem__(self, k):
        """
            Ok to get query slicing working properly we can't allow it
            to set limits on the internal query, because that is not the
            behavior we want, instead we slice the internal ordered_pk list
        """
        if not isinstance(k, (slice,) + six.integer_types):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."
        if self._result_cache is not None:
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self._clone()
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            qs.ordered_pks = qs.ordered_pks[start:stop]
            return list(qs)[::k.step] if k.step else qs

        qs = self._clone()
        qs.ordered_pks = [qs.ordered_pks[k], ]
        return list(qs)[0]


class RelatedIteratorManagerBase(object):
    def __init__(self, model, field, instance, reverse):
        super(RelatedIteratorManagerBase, self).__init__()
        self.model = model
        self.instance = instance
        self.field = field
        self.reverse = reverse

        if reverse:
            self.core_filters = {'%s__exact' % self.field.column: instance.pk}
        else:
            self.core_filters = {'pk__in': field.value_from_object(instance)}

    def get_queryset(self):
        db = self._db or router.db_for_read(self.instance.__class__, instance=self.instance)
        if self.field.default == list and not self.reverse:
            values = self.field.value_from_object(self.instance)
            qcls = OrderedQuerySet(self.model, using=db)
            qcls.ordered_pks = values[:]
        else:
            qcls = super(RelatedIteratorManagerBase, self).get_queryset()
        return (
            qcls.using(db)._next_is_sticky().filter(**self.core_filters)
        )

    def add(self, *values):
        for value in values:
            if not isinstance(value, self.model):
                raise TypeError("'%s' instance expected, got %r" % (self.model._meta.object_name, value))

            if not value.pk:
                raise ValueError("Model instances must be saved before they can be added to a related set")

            field_value = self.field.value_from_object(self.instance)
            # Depending on the type of iterable, but we want to maintain the
            # related .add() behavior
            if isinstance(field_value, list):
                field_value.append(value.pk)
            elif isinstance(field_value, set):
                field_value.add(value.pk)

    def remove(self, value):
        field_value = self.field.value_from_object(self.instance)
        # Depending on the type of iterable, but we want to maintain the
        # related .remove() behavior
        if isinstance(field_value, list):
            field_value.remove(value.pk)
        elif isinstance(field_value, set):
            field_value.discard(value.pk)

    def clear(self):
        setattr(self.instance, self.field.attname, self.field.default())

    def __len__(self):
        return len(self.field.value_from_object(self.instance))


def create_related_iter_manager(superclass, rel):
    """ Create a manager for the (reverse) relation which subclasses the related model's default manager. """
    class RelatedIteratorManager(RelatedIteratorManagerBase, superclass):
        pass
    return RelatedIteratorManager


class RelatedIteratorObjectsDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # multiple "remote" values and have a ManyToManyField pointed at them by
    # some other model (rather than having a ManyToManyField themselves).
    # In the example "publication.article_set", the article_set attribute is a
    # ManyRelatedObjectsDescriptor instance.
    def __init__(self, related):
        self.related = related   # RelatedObject instance

    @cached_property
    def related_manager_cls(self):
        """
            Dynamically create a class that subclasses the related
            model's default manager.
        """

        manager = self.related.related_model._default_manager.__class__

        return create_related_iter_manager(
            manager,
            self.related.field.rel
        )

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        rel_model = self.related.related_model
        rel_field = self.related.field

        manager = self.related_manager_cls(
            model=rel_model,
            field=rel_field,
            instance=instance,
            reverse=True
        )

        return manager

    def __set__(self, obj, value):
        raise AttributeError("You can't set the reverse relation directly")


class ReverseRelatedObjectsDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # multiple "remote" values and have a ManyToManyField defined in their
    # model (rather than having another model pointed *at* them).
    # In the example "article.publications", the publications attribute is a
    # ReverseManyRelatedObjectsDescriptor instance.
    def __init__(self, m2m_field):
        self.field = m2m_field

    @cached_property
    def related_manager_cls(self):
        # Dynamically create a class that subclasses the related model's
        # default manager.
        return create_related_iter_manager(
            self.field.rel.to._default_manager.__class__,
            self.field.rel.to
        )

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        manager = self.related_manager_cls(
            model=self.field.rel.to,
            field=self.field,
            instance=instance,
            reverse=False
        )

        return manager

    def __set__(self, obj, value):
        obj.__dict__[self.field.attname] = self.field.to_python([x.pk for x in value])


from abc import ABCMeta


class RelatedIteratorField(ForeignObject):

    __metaclass__ = ABCMeta

    requires_unique_target = False
    generate_reverse_relation = True
    empty_strings_allowed = False

    def __init__(self, to, limit_choices_to=None, related_name=None, on_delete=models.DO_NOTHING, **kwargs):
        # Make sure that we do nothing on cascade by default
        if on_delete == models.CASCADE:
            raise ImproperlyConfigured(
                "on_delete=CASCADE is disabled for iterable fields as this will "
                "wipe out the instance when the field still has related objects"
            )

        if on_delete in (models.SET_NULL, models.SET_DEFAULT):
            raise ImproperlyConfigured("Using an on_delete value of {} will cause undesirable behavior"
                             " (e.g. wipeout the entire list) if you really want to do that "
                             "then use models.SET instead and return an empty list/set")

        kwargs["rel"] = RelatedIteratorRel(
            self,
            to,
            related_name=related_name,
            limit_choices_to=limit_choices_to,
            on_delete=on_delete
        )

        if django.VERSION[1] >= 9:  # Django 1.8 doesn't have on_delete as attribute
            kwargs.update({
                'on_delete': models.DO_NOTHING,
            })

        from_fields = ['self']
        to_fields = [None]

        super(RelatedIteratorField, self).__init__(to, from_fields=from_fields, to_fields=to_fields, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(RelatedIteratorField, self).deconstruct()
        # We hardcode a number of arguments for RelatedIteratorField, those arguments need to be removed here
        for hardcoded_kwarg in ["to_fields", "from_fields", "on_delete"]:
            del kwargs[hardcoded_kwarg]

        return name, path, args, kwargs

    def get_attname(self):
        return '%s_ids' % self.name

    def get_attname_column(self):
        attname = self.get_attname()
        column = self.db_column or attname
        return attname, column

    def contribute_to_class(self, cls, name):
        # To support multiple relations to self, it's useful to have a non-None
        # related name on symmetrical relations for internal reasons. The
        # concept doesn't make a lot of sense externally ("you want me to
        # specify *what* on my non-reversible relation?!"), so we set it up
        # automatically. The funky name reduces the chance of an accidental
        # clash.
        if (self.rel.to == "self" or self.rel.to == cls._meta.object_name):
            self.rel.related_name = "%s_rel_+" % name

        super(RelatedIteratorField, self).contribute_to_class(cls, name)

        # Add the descriptor for the m2m relation
        setattr(cls, self.name, ReverseRelatedObjectsDescriptor(self))

    def contribute_to_related_class(self, cls, related):
        # Internal M2Ms (i.e., those with a related name ending with '+')
        # and swapped models don't get a related descriptor.
        if not self.rel.is_hidden() and not related.to._meta.swapped:
            setattr(cls, related.get_accessor_name(), RelatedIteratorObjectsDescriptor(related))


    def get_db_prep_save(self, *args, **kwargs):
        ret = super(RelatedIteratorField, self).get_db_prep_save(*args, **kwargs)

        if not ret:
            return None

        if isinstance(ret, set):
            ret = list(ret)
        return ret

    def get_db_prep_lookup(self, *args, **kwargs):
        ret = super(RelatedIteratorField, self).get_db_prep_lookup(*args, **kwargs)

        if not ret:
            return []

        if isinstance(ret, set):
            ret = list(ret)
        return ret

    def value_to_string(self, obj):
        """
        Custom method for serialization, as JSON doesn't support
        serializing sets.
        """
        return str(list(self._get_val_from_obj(obj)))


    def formfield(self, **kwargs):
        db = kwargs.pop('using', None)
        defaults = {
            'form_class': forms.ModelMultipleChoiceField,
            'queryset': self.rel.to._default_manager.using(db).complex_filter(self.rel.limit_choices_to)
        }
        defaults.update(kwargs)
        # If initial is passed in, it's a list of related objects, but the
        # MultipleChoiceField takes a list of IDs.
        if defaults.get('initial') is not None:
            initial = defaults['initial']
            if callable(initial):
                initial = initial()
            defaults['initial'] = [i._get_pk_val() for i in initial]
        return super(RelatedIteratorField, self).formfield(**defaults)


class RelatedSetField(RelatedIteratorField):

    def db_type(self, connection):
        return 'set'

    def __init__(self, *args, **kwargs):

        kwargs["default"] = set
        kwargs["null"] = True

        super(RelatedSetField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(RelatedSetField, self).deconstruct()
        # We hardcode a number of arguments for RelatedIteratorField, those arguments need to be removed here
        for hardcoded_kwarg in ["default", "null"]:
            del kwargs[hardcoded_kwarg]

        return name, path, args, kwargs

    def to_python(self, value):
        if value is None:
            return set()

        # Deal with deserialization from a string
        if isinstance(value, basestring):
            if not (value.startswith("[") and value.endswith("]")) and \
               not (value.startswith("{") and value.endswith("}")):
                raise ValidationError("Invalid input for RelatedSetField instance")

            value = value[1:-1].strip()

            if not value:
                return set()

            ids = [self.rel.to._meta.pk.to_python(x) for x in value.split(",")]
            # Annoyingly Django special cases FK and M2M in the Python deserialization code,
            # to assign to the attname, whereas all other fields (including this one) are required to
            # populate field.name instead. So we have to query here... we have no choice :(
            return set(self.rel.to._default_manager.db_manager('default').filter(pk__in=ids))

        return set(value)

    def save_form_data(self, instance, data):
        setattr(instance, self.attname, set()) #Wipe out existing things
        for value in data:
            # If this is a model instance then add the pk
            if isinstance(value, self.rel.to):
                value = value.pk

            field = getattr(instance, self.attname)
            field.add(value)


class RelatedListField(RelatedIteratorField):

    def db_type(self, connection):
        return 'list'

    def __init__(self, *args, **kwargs):

        kwargs["default"] = list
        kwargs["null"] = True

        super(RelatedListField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(RelatedListField, self).deconstruct()
        # We hardcode a number of arguments for RelatedIteratorField, those arguments need to be removed here
        for hardcoded_kwarg in ["default", "null"]:
            del kwargs[hardcoded_kwarg]

        return name, path, args, kwargs

    def to_python(self, value):
        if value is None:
            return list()

        # Deal with deserialization from a string
        if isinstance(value, basestring):
            if not (value.startswith("[") and value.endswith("]")):
                raise ValidationError("Invalid input for RelatedListField instance")

            value = value[1:-1].strip()

            if not value:
                return list()

            ids = [self.rel.to._meta.pk.to_python(x) for x in value.split(",")]
            # Annoyingly Django special cases FK and M2M in the Python deserialization code,
            # to assign to the attname, whereas all other fields (including this one) are required to
            # populate field.name instead. So we have to query here... we have no choice :(
            return list(self.rel.to._default_manager.db_manager('default').filter(pk__in=ids))

        return list(value)

    def save_form_data(self, instance, data):
        setattr(instance, self.attname, []) #Wipe out existing things
        for value in data:
            # If this is a model instance then grab the PK
            if isinstance(value, self.rel.to):
                value = value.pk

            # Add to the underlying list
            field = getattr(instance, self.attname)
            field.append(value)


class GRCreator(property):

    """
    This is like django.db.models.fields.subclassing.Creator, but does its
    magic on get instead of set.
    """

    def __init__(self, field):
        self.field = field
        self.attname = field.get_attname()
        super(GRCreator, self).__init__(self.get, self.set)

    def get(self, obj):
        cache_attr = "_{}_cache".format(self.attname)
        if getattr(obj, cache_attr, None) is None:
            setattr(obj, cache_attr, self.field.__get__(obj))
        return getattr(obj, cache_attr)

    def set(self, obj, value):
        obj.__dict__[self.attname] = self.field.get_prep_value(value)
        if isinstance(value, models.Model):
            setattr(obj, "_{}_cache".format(self.attname), value)


class GRReverseCreator(property):

    """Prevent forms setting whatever_id to an object"""

    def __init__(self, field):
        self.field = field
        self.attname = field.get_attname()
        super(GRReverseCreator, self).__init__(self.get, self.set)

    def get(self, obj):
        return obj.__dict__[self.attname]

    def set(self, obj, value):
        if not isinstance(value, basestring):
            value = self.field.get_prep_value(value)
        obj.__dict__[self.attname] = value


class GenericRelationField(models.Field):
    """ Similar to django.contrib.contenttypes.generic.GenericForeignKey, but
        doesn't require all of the contenttypes cruft.

        Empty NULL values are specifically encoded so they can also be unique, this is different
        from Django's FK behaviour.
    """
    description = "Generic one-way relation field"
    form_class = GenericRelationFormfield

    def __init__(self, *args, **kwargs):
        kwargs.update(
            max_length=255,
        )

        if 'db_index' not in kwargs:
            kwargs['db_index'] = True

        super(GenericRelationField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(GenericRelationField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, GRCreator(self))
        setattr(cls, self.attname, GRReverseCreator(self))

    def get_attname(self):
        return "{}_id".format(self.name)

    def set_attributes_from_name(self, name):
        super(GenericRelationField, self).set_attributes_from_name(name)

    @classmethod
    def encode_pk(cls, pk, obj_cls):
        return encode_pk(pk, obj_cls)

    def get_internal_type(self):
        return "CharField"

    def get_prep_value(cls, value):
        return cls.form_class.to_string(value)

    def __get__(self, instance):
        if instance is None:
            return self

        value = getattr(instance, self.attname)

        from djangae.forms.fields import decode_pk
        from djangae.db.utils import get_model_from_db_table

        if value is None:
            return None

        model_ref, pk = decode_pk(value)
        try:
            return get_model_from_db_table(model_ref).objects.get(pk=pk)
        except AttributeError:
            raise ImproperlyConfigured("Unable to find model with db_table: {}".format(model_ref))

    def formfield(self, **kwargs):
        defaults = {
            'form_class': self.form_class,
        }
        defaults.update(kwargs)
        return super(GenericRelationField, self).formfield(**defaults)

    def get_validator_unique_lookup_type(self):
        raise NotImplementedError()
