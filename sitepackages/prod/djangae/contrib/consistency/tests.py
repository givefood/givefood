# SYSTEM
from __future__ import absolute_import
import unittest

# LIBRARIES
from djangae.test import inconsistent_db
from django.db import models
from django.test import TestCase
from django.test.utils import override_settings

# CONSISTENCY
from djangae.contrib.consistency import improve_queryset_consistency
from djangae.contrib.consistency.signals import connect_signals, disconnect_signals


class TestModel(models.Model):
    name = models.CharField(max_length=100)


class ConsistencyTests(TestCase):

    def setUp(self):
        super(ConsistencyTests, self).setUp()
        # Having post-delete signals registered changes the way that django does its delete queries
        # so to avoid causing django tests to fail (which are run as part of the 'testapp' tests in
        # djangae) we only register the consistency signals during our tests
        connect_signals()

    def tearDown(self):
        disconnect_signals()
        super(ConsistencyTests, self).tearDown()

    def test_newly_created_objects_returned(self):
        existing = TestModel.objects.create(name='existing')
        queryset = TestModel.objects.all()
        self.assertItemsEqual(queryset.all(), [existing])
        # Add a new object with eventual consistency being slow
        with inconsistent_db():
            new = TestModel.objects.create(name='new')
            # The new object should not yet be returned
            self.assertItemsEqual(queryset.all(), [existing])
            # But using our handy function it should be returned
            consistent = improve_queryset_consistency(queryset)
            self.assertItemsEqual(consistent.all(), [existing, new])

    @override_settings(CONSISTENCY_CONFIG={"defaults": {"cache_on_modification": True}})
    def test_newly_modified_objects_returned(self):
        """ If an object which previously did not match the query is modified to now match it, then
            improve_queryset_consistency should include it even when the DB hasn't caught up yet.
        """
        obj = TestModel.objects.create(name='A')
        queryset = TestModel.objects.filter(name='B')
        self.assertEqual(queryset.all().count(), 0)
        with inconsistent_db():
            obj.name = 'B'
            obj.save()
            # The DB is inconsistent, so the queryset should still return nothing
            self.assertEqual(queryset.all().count(), 0)
            # But improve_queryset_consistency should include the object
            consistent = improve_queryset_consistency(queryset)
            self.assertEqual(consistent.all().count(), 1)

    def test_stale_objects_not_returned(self):
        """ When an object is modified to no longer match a query,
            improve_queryset_consistency should ensure that it is not returned.
        """
        obj = TestModel.objects.create(name='A')
        queryset = TestModel.objects.filter(name='A')
        self.assertItemsEqual(queryset.all(), [obj])
        with inconsistent_db():
            obj.name = 'B'
            obj.save()
            # The object no longer matches the query, but the inconsistent db will still return it
            self.assertItemsEqual(queryset.all(), [obj])
            # improve_queryset_consistency to the rescue!
            consistent = improve_queryset_consistency(queryset)
            self.assertEqual(consistent.count(), 0)

    @unittest.skip("Can't get the DB to be inconsistent to test this!")
    def test_deleted_objects_not_returned(self):
        """ When an object is deleted, improve_queryset_consistency should ensure that it is not
            returned.
        """
        obj = TestModel.objects.create(name='A')
        queryset = TestModel.objects.filter(name='A')
        self.assertItemsEqual(queryset.all(), [obj])
        with inconsistent_db():
            obj.delete()
            # The object no longer exists, but the inconsistent db will still return it
            self.assertItemsEqual(queryset.all(), [obj])
            # improve_queryset_consistency to the rescue!
            consistent = improve_queryset_consistency(queryset)
            self.assertEqual(consistent.count(), 0)

    def test_ordering_retained(self):
        """ Test that using improve_queryset_consistency still retains the ordering. """
        b = TestModel.objects.create(name='B')
        a = TestModel.objects.create(name='A')
        c = TestModel.objects.create(name='C')
        queryset = TestModel.objects.all().order_by('name')
        # To be sure that we test a query which combines the Datastore result with our cache we
        # include some inconsistent_db stuff here...
        with inconsistent_db():
            d = TestModel.objects.create(name='D')
            queryset = improve_queryset_consistency(queryset)
            self.assertEqual(list(queryset), [a, b, c, d])
