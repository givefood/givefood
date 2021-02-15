"""
    Tests for "special indexing" (E.g. __contains, __startswith etc.)
"""
import logging

from djangae.contrib import sleuth
from djangae.db.caching import disable_cache
from djangae.test import TestCase

from django.core.management import call_command
from django.db import connection
from django.db import models


class ContainsModel(models.Model):
    field1 = models.CharField(max_length=500)


class ContainsIndexerTests(TestCase):

    def _list_contains_model_tables(self):
        with connection.cursor() as cursor:
            return [
                x for x in connection.introspection.table_names(cursor)
                if ContainsModel._meta.db_table in x
            ]

    def test_basic_usage(self):
        c1 = ContainsModel.objects.create(field1="Adam")
        c2 = ContainsModel.objects.create(field1="Luke")
        ContainsModel.objects.create(field1="Lvke")  # 'v' is the next character after 'u'

        self.assertEqual(ContainsModel.objects.filter(field1__contains="Ad").first(), c1)
        self.assertEqual(ContainsModel.objects.filter(field1__contains="Lu").first(), c2)
        self.assertEqual(ContainsModel.objects.filter(field1__contains="da").first(), c1)
        self.assertEqual(ContainsModel.objects.filter(field1__contains="ke").first(), c2)

    @disable_cache()
    def test_queryset_instantiation_does_not_trigger_queries(self):
        """ The `contains` behaviour should only trigger DB calls when the queryset is evaluated,
            not when the queryset is created.
        """
        ContainsModel.objects.create(field1="Adam")
        with sleuth.watch("djangae.db.backends.appengine.rpc.Query.Run") as datastore_query:
            with sleuth.watch("djangae.db.backends.appengine.rpc.Get") as datastore_get:
                queryset = ContainsModel.objects.filter(field1__contains="Ad")
                self.assertFalse(datastore_query.called)
                self.assertFalse(datastore_get.called)
                logging.debug('datastore_query.calls count: %d', len(datastore_query.calls))
                list(queryset)
                self.assertTrue(datastore_query.called)
                logging.debug('datastore_query.called count: %d', datastore_query.called)
                self.assertTrue(datastore_get.called)

    def test_flush_wipes_descendent_kinds(self):
        """
            The contains index generates a kind for each model field which
            uses a __contains index. When we flush the database these kinds should also
            be wiped if their "parent" model table is wiped
        """

        ContainsModel.objects.create(field1="Vera")

        table_names = self._list_contains_model_tables()

        self.assertItemsEqual([
            ContainsModel._meta.db_table,
            "_djangae_idx_{}_field1".format(ContainsModel._meta.db_table)
        ], table_names)

        # Flush the database
        call_command('flush', interactive=False, load_initial_data=False)

        # Should be zero tables!
        self.assertFalse(self._list_contains_model_tables(), self._list_contains_model_tables())

    def test_delete_wipes_descendent_index_tables(self):
        c1 = ContainsModel.objects.create(field1="Phil")
        c1.delete()
        self.assertFalse(self._list_contains_model_tables(), self._list_contains_model_tables())
