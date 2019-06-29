import random
from functools import partial
from djangae.fields import ComputedCharField
from django.db.models.fields import FieldDoesNotExist

NULL_CHARACTER = u"\0"


def generator(fields, instance):
    """
        Calculates the value needed for a unique ordered representation of the fields
        we are paginating.
    """
    values = []
    for field in fields:
        neg = field.startswith("-")

        # If the field we have to paginate by is the pk, get the pk field name.
        if field == 'pk':
            field = instance._meta.pk.name

        value = instance._meta.get_field(field.lstrip("-")).value_from_object(instance)

        if hasattr(value, "isoformat"):
            value = value.isoformat()

        value = unicode(value)

        if neg:
            # this creates the alphabetical mirror of a string, e.g. ab => zy, but for the full
            # range of unicode characters, e.g. first unicode char => last unicode char, etc
            value = u"".join([ unichr(0xffff - ord(x)) for x in value ])
        values.append(value)

    values.append(unicode(instance.pk) if instance.pk else unicode(random.randint(0, 1000000000)))

    return NULL_CHARACTER.join(values)


def _field_name_for_ordering(ordering):
    names = []

    # A single negated ordering can use the same field (we just flip the query)
    # so we normalize that out here and use the same field in that case
    if len(ordering) == 1 and ordering[0].startswith("-"):
        ordering = (ordering[0].lstrip("-"),)

    for field in ordering:
        if field.startswith("-"):
            names.append("neg_" + field[1:])
        else:
            names.append(field)

    new_field_name = "pagination_{}".format("_".join(names))
    return new_field_name


class PaginatedModel(object):
    """
        A class decorator which automatically generates pre-calculated fields for pagination.

        Specify the orderings (as a list of field tuples) you intend to paginate your models on, and
        additional fields will be added to the model which automatically calculate the appropriate
        value for pagination to work.

        The DatastorePaginator class will implicitly convert your query order_by to use these generated
        fields. Markers will be cached at the end of each page for each query, so that skipping pages
        is fast even when there are many pages.
    """
    def __init__(self, orderings):
        # Allow orderings to be specified either as single fields, or tuples/lists of fields
        _orderings = []
        for ordering in orderings:
            if isinstance(ordering, basestring):
                _orderings.append((ordering,))
            else:
                _orderings.append(ordering)
        self.orderings = _orderings

    def __call__(self, cls):
        """
            Dynamically adds pagination fields to a model depending on
            the orderings you specify
        """
        for ordering in self.orderings:
            new_field_name = _field_name_for_ordering(ordering)
            try:
                cls._meta.get_field(new_field_name)
            except FieldDoesNotExist:
                ComputedCharField(
                    partial(generator, ordering), max_length=500, editable=False
                ).contribute_to_class(cls, new_field_name)

        return cls

paginated_model = PaginatedModel
