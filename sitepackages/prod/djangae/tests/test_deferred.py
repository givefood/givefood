from django.db import models

from djangae.contrib import sleuth
from djangae.deferred import defer
from djangae.test import TestCase, TaskFailedError


def test_task(*args, **kwargs):
    pass


def assert_cache_wiped(instance):
    cache_name = DeferModelA._meta.get_field("b").get_cache_name()
    assert(getattr(instance, cache_name, None) is None)


class DeferModelA(models.Model):
    b = models.ForeignKey("DeferModelB")

    class Meta:
        app_label = "djangae"


class DeferModelB(models.Model):
    class Meta:
        app_label = "djangae"


class DeferTests(TestCase):
    def test_defer_uses_an_entity_group(self):
        with sleuth.watch('google.appengine.api.datastore.Put') as Put:
            defer(test_task)
            self.assertTrue(Put.called)

        with sleuth.watch('google.appengine.api.datastore.Put') as Put:
            defer(test_task, _small_task=True)
            self.assertFalse(Put.called)

    def test_wipe_related_caches(self):
        b = DeferModelB.objects.create()
        a = DeferModelA.objects.create(b=b)
        a.b  # Make sure we access it

        cache_name = DeferModelA._meta.get_field("b").get_cache_name()
        self.assertTrue(getattr(a, cache_name))

        defer(assert_cache_wiped, a)

        # Should raise an assertion error if the cache existed
        try:
            self.process_task_queues()
        except TaskFailedError as e:
            raise e.original_exception

        # Should not have wiped the cache for us!
        self.assertIsNotNone(getattr(a, cache_name, None))

    def test_queues_task(self):
        initial_count = self.get_task_count()
        defer(test_task)
        self.assertEqual(self.get_task_count(), initial_count + 1)
