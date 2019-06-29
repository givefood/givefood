import collections

from django.utils import six
from django.core.paginator import PageNotAnInteger, EmptyPage


class DatastorePaginator(object):
    """
    A paginator which only supports previous/next page controls and avoids doing
    expensive count() calls on datastore-backed queries.

    Does not implement the full Paginator API.
    """

    NOT_SUPPORTED_MSG = "Property '{}' is not supported when paginating datastore-models"

    def __init__(self, object_list, per_page, orphans=0,
                 allow_empty_first_page=True):
        self.fetched_objects = object_list
        self.object_list = []
        self.per_page = int(per_page)
        self.allow_empty_first_page = allow_empty_first_page

    def validate_number(self, number):
        """
        Validates the given 1-based page number.
        """
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise PageNotAnInteger('That page number is not an integer')
        if number < 1:
            raise EmptyPage('That page number is less than 1')
        return number

    def page(self, number):
        """
        Returns a Page object for the given 1-based page number.
        """
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        self.fetched_objects = self.fetched_objects[bottom:top + 1]
        self.object_list = self.fetched_objects[:self.per_page]

        return DatastorePage(self.fetched_objects, self.object_list, number, self)

    def _get_count(self):
        """
        Returns the total number of objects, across all pages.
        """
        raise NotImplementedError(self.NOT_SUPPORTED_MSG.format('count'))
    count = property(_get_count)

    def _get_num_pages(self):
        """
        Returns the total number of pages.
        """
        raise NotImplementedError(self.NOT_SUPPORTED_MSG.format('num_pages'))
    num_pages = property(_get_num_pages)

    def _get_page_range(self):
        """
        Returns a 1-based range of pages for iterating through within
        a template for loop.
        """
        raise NotImplementedError(self.NOT_SUPPORTED_MSG.format('page_range'))
    page_range = property(_get_page_range)


Paginator = DatastorePaginator


class DatastorePage(collections.Sequence):

    def __init__(self, fetched_objects, object_list, number, paginator):
        self.fetched_objects = fetched_objects
        self.object_list = object_list
        self.number = number
        self.paginator = paginator

    def __repr__(self):
        bottom = (self.number - 1) * self.paginator.per_page
        top = len(self.object_list)
        return '<Objects {0} to {1}>'.format(bottom, top)

    def __len__(self):
        return len(self.object_list)

    def __getitem__(self, index):
        if not isinstance(index, (slice,) + six.integer_types):
            raise TypeError
        # The object_list is converted to a list so that if it was a QuerySet
        # it won't be a database hit per __getitem__.
        if not isinstance(self.object_list, list):
            self.object_list = list(self.object_list)
        return self.object_list[index]

    def has_next(self):
        return len(self.fetched_objects) > len(self.object_list)

    def has_previous(self):
        return self.number > 1

    def has_other_pages(self):
        return self.has_previous() or self.has_next()

    def next_page_number(self):
        return self.paginator.validate_number(self.number + 1)

    def previous_page_number(self):
        return self.paginator.validate_number(self.number - 1)

    def start_index(self):
        """
        Returns the 1-based index of the first object on this page,
        relative to total objects in the paginator.
        """
        # Special case, return zero if no items.
        if self.number == 1 and len(self.object_list) == 0:
            return 0
        return (self.paginator.per_page * (self.number - 1)) + 1

    def end_index(self):
        """
        Returns the 1-based index of the last object on this page,
        relative to total objects found (hits).
        """
        return (self.paginator.per_page * (self.number - 1)) + len(self.object_list)


Page = DatastorePage
