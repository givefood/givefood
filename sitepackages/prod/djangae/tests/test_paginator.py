"""
    Tests for djangae.core.paginator to make sure that never does a full
    count on a query.
"""
from django.db import models
from django.utils.six.moves import range

from djangae.contrib import sleuth
from djangae.test import TestCase
from djangae.core.paginator import Paginator


class SimplePaginatedModel(models.Model):
    field1 = models.IntegerField(default=0)
    field2 = models.CharField(max_length=10)


class PaginatorTests(TestCase):
    def setUp(self):
        super(PaginatorTests, self).setUp()

        self.instances = [
            SimplePaginatedModel.objects.create(field1=x, field2=str(x+1))
            for x in range(10)
        ]

    def test_no_previous_on_first_page(self):
        with sleuth.watch('djangae.db.backends.appengine.commands.datastore.Query.Run') as query:
            paginator = Paginator(SimplePaginatedModel.objects.all(), 2)

            self.assertFalse(query.called)
            page = paginator.page(1)
            self.assertFalse(page.has_previous())

            page = paginator.page(2)
            self.assertTrue(page.has_previous())

    def test_no_next_on_last_page(self):
        paginator = Paginator(SimplePaginatedModel.objects.all(), 2)
        page = paginator.page(5)
        self.assertTrue(page.has_previous())
        self.assertFalse(page.has_next())

        page = paginator.page(4)
        self.assertTrue(page.has_previous())
        self.assertTrue(page.has_next())

    def test_count_raises_error(self):
        paginator = Paginator(SimplePaginatedModel.objects.all(), 2)
        with self.assertRaises(NotImplementedError):
            paginator.count

    def test_num_pages_raises_error(self):
        paginator = Paginator(SimplePaginatedModel.objects.all(), 2)
        with self.assertRaises(NotImplementedError):
            paginator.num_pages

    def test_page_runs_limited_query(self):
         with sleuth.watch('djangae.db.backends.appengine.commands.datastore.Query.Run') as query:
            paginator = Paginator(SimplePaginatedModel.objects.all(), 2)

            self.assertFalse(query.called)
            page = paginator.page(1)
            self.assertFalse(page.has_previous())
            self.assertTrue(page.has_next())
            self.assertTrue(query.called)

            # Should've queried for 1 more than we asked to determine if there is a next
            # page or not
            self.assertEqual(query.calls[0].kwargs["limit"], 3)
            self.assertEqual(len(page.object_list), 2)

    def test_results_correct(self):
        paginator = Paginator(SimplePaginatedModel.objects.all(), 2)
        page = paginator.page(2)

        self.assertEqual(page[0].field1, 2)
        self.assertEqual(page[1].field1, 3)

        page = paginator.page(3)

        self.assertEqual(page[0].field1, 4)
        self.assertEqual(page[1].field1, 5)
