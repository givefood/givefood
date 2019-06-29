from hashlib import md5
from django.db import models
from django.conf import settings
from unittest import skipIf

from google.appengine.api import datastore, datastore_errors

from .models import UniqueAction, encode_model
from djangae.test import TestCase, process_task_queues
from djangae.db.constraints import UniqueMarker, UniquenessMixin


DEFAULT_NAMESPACE = settings.DATABASES.get("default", {}).get("NAMESPACE")


class TestModel(UniquenessMixin, models.Model):
    name = models.CharField(max_length=32, unique=True)
    counter1 = models.IntegerField()
    counter2 = models.IntegerField()

    class Meta:
        unique_together = [('counter1', 'counter2')]


class MapperTests(TestCase):

    def setUp(self):
        super(MapperTests, self).setUp()
        self.i1 = TestModel.objects.create(name="name1", counter1=1, counter2=1)
        self.i2 = TestModel.objects.create(name="name3", counter1=1, counter2=2)
        self.i3 = self.i4 = None

    def tearDown(self):
        if self.i3:
            self.i3.delete()
        if self.i4:
            self.i4.delete()

        super(MapperTests, self).tearDown()

    def test_check_ok(self):
        # A check should produce no errors.
        UniqueAction.objects.create(action_type="check", model=encode_model(TestModel))
        process_task_queues()

        a = UniqueAction.objects.get()
        self.assertEqual(a.status, "done")
        self.assertEqual(0, a.actionlog_set.count())

    def test_check_missing_markers(self):
        marker1 = "{}|name:{}".format(TestModel._meta.db_table, md5(self.i2.name).hexdigest())
        marker_key = datastore.Key.from_path(UniqueMarker.kind(), marker1, namespace=DEFAULT_NAMESPACE)
        datastore.Delete(marker_key)
        UniqueAction.objects.create(action_type="check", model=encode_model(TestModel))
        process_task_queues()

        a = UniqueAction.objects.get()
        self.assertEqual(a.status, "done")
        self.assertEqual(1, a.actionlog_set.count())
        error = a.actionlog_set.all()[0]
        instance_key = datastore.Key.from_path(TestModel._meta.db_table, self.i2.pk, namespace=DEFAULT_NAMESPACE)
        self.assertEqual(error.log_type, "missing_marker")
        self.assertEqual(error.instance_key, str(instance_key))
        self.assertEqual(error.marker_key, str(marker_key))

    def test_check_missing_instance_attr(self):
        marker1 = "{}|name:{}".format(TestModel._meta.db_table, md5(self.i2.name).hexdigest())
        marker_key = datastore.Key.from_path(UniqueMarker.kind(), marker1, namespace=DEFAULT_NAMESPACE)
        marker = datastore.Get(marker_key)
        marker['instance'] = None
        datastore.Put(marker)

        UniqueAction.objects.create(action_type="check", model=encode_model(TestModel))
        process_task_queues()

        a = UniqueAction.objects.get()
        self.assertEqual(a.status, "done")
        self.assertEqual(1, a.actionlog_set.count())
        error = a.actionlog_set.all()[0]
        instance_key = datastore.Key.from_path(TestModel._meta.db_table, self.i2.pk, namespace=DEFAULT_NAMESPACE)
        self.assertEqual(error.log_type, "missing_instance")
        self.assertEqual(error.instance_key, str(instance_key))
        self.assertEqual(error.marker_key, str(marker_key))

    def test_repair_missing_markers(self):
        instance_key = datastore.Key.from_path(TestModel._meta.db_table, self.i2.pk, namespace=DEFAULT_NAMESPACE)
        marker1 = "{}|name:{}".format(TestModel._meta.db_table, md5(self.i2.name).hexdigest())
        marker_key = datastore.Key.from_path(UniqueMarker.kind(), marker1, namespace=DEFAULT_NAMESPACE)
        datastore.Delete(marker_key)
        UniqueAction.objects.create(action_type="repair", model=encode_model(TestModel))
        process_task_queues()

        a = UniqueAction.objects.get()
        self.assertEqual(a.status, "done")
        self.assertEqual(0, a.actionlog_set.count())
        # Is the missing marker restored?
        marker = datastore.Get(marker_key)
        self.assertTrue(marker)
        self.assertTrue(isinstance(marker["instance"], datastore.Key))
        self.assertEqual(instance_key, marker["instance"])
        self.assertTrue(marker["created"])

    def test_check_old_style_marker(self):
        instance_key = datastore.Key.from_path(TestModel._meta.db_table, self.i2.pk, namespace=DEFAULT_NAMESPACE)

        marker1 = "{}|name:{}".format(TestModel._meta.db_table, md5(self.i2.name).hexdigest())
        marker_key = datastore.Key.from_path(UniqueMarker.kind(), marker1, namespace=DEFAULT_NAMESPACE)
        marker = datastore.Get(marker_key)
        marker['instance'] = str(instance_key) #Make the instance a string
        datastore.Put(marker)

        UniqueAction.objects.create(action_type="check", model=encode_model(TestModel))
        process_task_queues()

        a = UniqueAction.objects.get()
        self.assertEqual(a.status, "done")
        self.assertEqual(1, a.actionlog_set.count())
        error = a.actionlog_set.all()[0]

        self.assertEqual(error.log_type, "old_instance_key")
        self.assertEqual(error.instance_key, str(instance_key))
        self.assertEqual(error.marker_key, str(marker_key))

    def test_repair_old_style_marker(self):
        instance_key = datastore.Key.from_path(TestModel._meta.db_table, self.i2.pk, namespace=DEFAULT_NAMESPACE)

        marker1 = "{}|name:{}".format(TestModel._meta.db_table, md5(self.i2.name).hexdigest())
        marker_key = datastore.Key.from_path(UniqueMarker.kind(), marker1, namespace=DEFAULT_NAMESPACE)
        marker = datastore.Get(marker_key)
        marker['instance'] = str(instance_key) #Make the instance a string
        datastore.Put(marker)

        UniqueAction.objects.create(action_type="repair", model=encode_model(TestModel))
        process_task_queues()

        a = UniqueAction.objects.get()
        self.assertEqual(a.status, "done")
        self.assertEqual(0, a.actionlog_set.count())
        marker = datastore.Get(marker_key)
        self.assertTrue(marker)
        self.assertEqual(marker['instance'], instance_key)

    def test_repair_missing_instance_attr(self):
        instance_key = datastore.Key.from_path(TestModel._meta.db_table, self.i2.pk, namespace=DEFAULT_NAMESPACE)
        marker1 = "{}|name:{}".format(TestModel._meta.db_table, md5(self.i2.name).hexdigest())
        marker_key = datastore.Key.from_path(UniqueMarker.kind(), marker1, namespace=DEFAULT_NAMESPACE)
        marker = datastore.Get(marker_key)
        marker['instance'] = None
        datastore.Put(marker)

        UniqueAction.objects.create(action_type="repair", model=encode_model(TestModel))
        process_task_queues()

        a = UniqueAction.objects.get()
        self.assertEqual(a.status, "done")
        self.assertEqual(0, a.actionlog_set.count())
        marker = datastore.Get(marker_key)
        self.assertTrue(marker)
        self.assertEqual(marker['instance'], instance_key)

    def test_clean_after_instance_deleted(self):
        marker1 = "{}|name:{}".format(TestModel._meta.db_table, md5(self.i1.name).hexdigest())
        marker_key = datastore.Key.from_path(UniqueMarker.kind(), marker1, namespace=DEFAULT_NAMESPACE)

        self.assertTrue(datastore.Get(marker_key))

        datastore.Delete(datastore.Key.from_path(TestModel._meta.db_table, self.i1.pk, namespace=DEFAULT_NAMESPACE)) # Delete the first instance

        self.assertTrue(datastore.Get(marker_key))

        UniqueAction.objects.create(action_type="clean", model=encode_model(TestModel))
        process_task_queues()

        self.assertRaises(datastore_errors.EntityNotFoundError, datastore.Get, marker_key)

    def test_clean_removes_markers_with_different_values(self):
        marker1 = "{}|name:{}".format(TestModel._meta.db_table, md5(self.i1.name).hexdigest())
        marker_key = datastore.Key.from_path(UniqueMarker.kind(), marker1, namespace=DEFAULT_NAMESPACE)

        original_marker = datastore.Get(marker_key)

        marker2 = "{}|name:{}".format(TestModel._meta.db_table, md5("bananas").hexdigest())

        new_marker = datastore.Entity(UniqueMarker.kind(), name=marker2, namespace=DEFAULT_NAMESPACE)
        new_marker.update(original_marker)
        datastore.Put(new_marker)

        UniqueAction.objects.create(action_type="clean", model=encode_model(TestModel))
        process_task_queues()

        self.assertRaises(datastore_errors.EntityNotFoundError, datastore.Get, new_marker.key())
        self.assertTrue(datastore.Get(marker_key))

    @skipIf("ns1" not in settings.DATABASES, "This test is designed for the Djangae testapp settings")
    def test_clean_removes_markers_with_different_values_on_non_default_namespace(self):
        self.i3 = TestModel.objects.using("ns1").create(id=self.i1.pk, name="name1", counter1=1, counter2=1)
        self.i4 = TestModel.objects.using("ns1").create(id=self.i2.pk, name="name3", counter1=1, counter2=2)

        NS1_NAMESPACE = settings.DATABASES["ns1"]["NAMESPACE"]

        marker1 = "{}|name:{}".format(TestModel._meta.db_table, md5(self.i3.name).hexdigest())
        marker_key = datastore.Key.from_path(UniqueMarker.kind(), marker1, namespace=NS1_NAMESPACE)
        default_key = datastore.Key.from_path(UniqueMarker.kind(), marker1, namespace=DEFAULT_NAMESPACE)
        original_marker = datastore.Get(marker_key)
        default_marker = datastore.Get(default_key)

        marker2 = "{}|name:{}".format(TestModel._meta.db_table, md5("bananas").hexdigest())
        new_marker = datastore.Entity(UniqueMarker.kind(), name=marker2, namespace=NS1_NAMESPACE)
        new_marker.update(original_marker)
        datastore.Put(new_marker)

        # This allows us to test: 1) namespaced markers will check against their namespace models (not all of them)"
        self.i1.delete()
        #... 2) the mapper only cleans the desired namespace
        datastore.Put(default_marker)

        UniqueAction.objects.create(action_type="clean", model=encode_model(TestModel), db="ns1")
        process_task_queues()

        self.assertRaises(datastore_errors.EntityNotFoundError, datastore.Get, new_marker.key())
        self.assertTrue(datastore.Get(default_marker.key()))
        self.assertTrue(datastore.Get(marker_key))
        datastore.Delete(default_marker)

    @skipIf("ns1" not in settings.DATABASES, "This test is designed for the Djangae testapp settings")
    def test_repair_missing_markers_on_non_default_namespace(self):
        self.i3 = TestModel.objects.using("ns1").create(id=self.i1.pk, name="name1", counter1=1, counter2=1)
        self.i4 = TestModel.objects.using("ns1").create(id=self.i2.pk, name="name3", counter1=1, counter2=2)
        NS1_NAMESPACE = settings.DATABASES["ns1"]["NAMESPACE"]

        instance_key = datastore.Key.from_path(TestModel._meta.db_table, self.i2.pk, namespace=DEFAULT_NAMESPACE)
        instance_key_ns1 = datastore.Key.from_path(TestModel._meta.db_table, self.i2.pk, namespace=NS1_NAMESPACE)
        marker = "{}|name:{}".format(TestModel._meta.db_table, md5(self.i2.name).hexdigest())
        marker_key_default = datastore.Key.from_path(UniqueMarker.kind(), marker, namespace=DEFAULT_NAMESPACE)
        marker_key_ns1 = datastore.Key.from_path(UniqueMarker.kind(), marker, namespace=NS1_NAMESPACE)
        datastore.Delete(marker_key_ns1)
        datastore.Delete(marker_key_default)

        UniqueAction.objects.create(action_type="repair", model=encode_model(TestModel), db="ns1")
        process_task_queues()

        a = UniqueAction.objects.get()
        self.assertEqual(a.status, "done")

        # Is the missing marker for the default namespace left alone?
        self.assertRaises(datastore_errors.EntityNotFoundError, datastore.Get, marker_key_default)
        # Is the missing marker restored?
        marker = datastore.Get(marker_key_ns1)
        self.assertTrue(marker)
        self.assertTrue(isinstance(marker["instance"], datastore.Key))
        self.assertEqual(instance_key_ns1, marker["instance"])
        self.assertTrue(marker["created"])
