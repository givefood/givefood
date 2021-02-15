import time

from mapreduce import output_writers
from django.db import models
from djangae.test import TestCase
from unittest import skipIf

from django.db import connection
from django.core.files.base import ContentFile
from djangae.storage import CloudStorage, has_cloudstorage
from django.test.utils import override_settings
from djangae.contrib.processing.mapreduce import (
    map_files,
    map_queryset,
    map_entities,
    map_reduce_queryset,
    map_reduce_entities,
    get_pipeline_by_id,
)

from google.appengine.api import datastore


class TestModel(models.Model):
    class Meta:
        app_label = "mapreduce"

    is_true = models.BooleanField(default=False)
    text = models.CharField(null=True, max_length=50)


class Counter(models.Model):
    count = models.PositiveIntegerField(default=0)


def count(instance, counter_id):
    counter = Counter.objects.get(pk=counter_id)
    counter.count = models.F('count') + 1
    counter.save()

def slow_count(instance, counter_id, sleep_duration):
    time.sleep(sleep_duration)
    count(instance, counter_id)

def count_entity_to_default_counter(entity):
    """ Dirty hack to work around the fact that when using  `map_reduce_entities` we cannot pass
        any params to the map_func, and therefore this function only accepts a single arg of the
        `entity` and just assumes that there's only 1 Counter object!
    """
    counter = Counter.objects.get()
    counter.count = models.F('count') + 1
    counter.save()


def count_contents(file_obj, counter_id):
    counter = Counter.objects.get(pk=counter_id)
    counter.count = models.F('count') + len(file_obj.read())
    counter.save()


def yield_letters(instance):
    if hasattr(instance, 'text'):
        text = instance.text
    else:
        text = instance.get('text', '')
    for letter in text:
        yield (letter, "")


def reduce_count(key, values):
    yield (key, len(values))


def delete(*args, **kwargs):
    TestModel.objects.all().delete()

class MapReduceEntityTests(TestCase):

    def setUp(self):
        for i in range(5):
            TestModel.objects.create(
                id=i+1,
                text="abcc-%s" % i
            )

    def test_filters(self):
        """ Passing the `_filters` kwarg to to `map_reduce_entities` should allow only some
            entities to be processed.
        """
        counter = Counter.objects.create()
        pipeline = map_reduce_entities(
            TestModel._meta.db_table,
            connection.settings_dict["NAMESPACE"],
            count_entity_to_default_counter,
            reduce_count,  # This is a no-op because count_entity doesn't return anything
            output_writers.GoogleCloudStorageKeyValueOutputWriter,
            _output_writer_kwargs={
                'bucket_name': 'test-bucket'
            },
            _filters=[("text", "=", "abcc-3")]
        )
        self.process_task_queues()
        # Refetch the pipeline record
        pipeline = get_pipeline_by_id(pipeline.pipeline_id)
        self.assertTrue(pipeline.has_finalized)
        # We expect only the one entity to have been counted
        counter.refresh_from_db()
        self.assertEqual(counter.count, 1)

    def test_mapreduce_over_entities(self):
        pipeline = map_reduce_entities(
            TestModel._meta.db_table,
            connection.settings_dict["NAMESPACE"],
            yield_letters,
            reduce_count,
            output_writers.GoogleCloudStorageKeyValueOutputWriter,
            _output_writer_kwargs={
                'bucket_name': 'test-bucket'
            }
        )
        self.process_task_queues()
        # Refetch the pipeline record
        pipeline = get_pipeline_by_id(pipeline.pipeline_id)
        self.assertTrue(pipeline.has_finalized)


class MapReduceQuerysetTests(TestCase):

    def setUp(self):
        for i in range(5):
            TestModel.objects.create(
                id=i+1,
                text="abcc"
            )

    def test_mapreduce_over_queryset(self):
        pipeline = map_reduce_queryset(
            TestModel.objects.all(),
            yield_letters,
            reduce_count,
            output_writers.GoogleCloudStorageKeyValueOutputWriter,
            _output_writer_kwargs={
                'bucket_name': 'test-bucket'
            }
        )
        self.process_task_queues()
        pipeline = get_pipeline_by_id(pipeline.pipeline_id)
        self.assertTrue(pipeline.has_finalized)


class MapQuerysetTests(TestCase):
    def setUp(self):
        for i in range(5):
            TestModel.objects.create(id=i+1)

    def test_filtering(self):
        counter = Counter.objects.create()
        pipeline = map_queryset(
            TestModel.objects.filter(is_true=True),
            count,
            finalize_func=delete,
            counter_id=counter.pk
        )
        counter = Counter.objects.create()
        self.process_task_queues()
        pipeline = get_pipeline_by_id(pipeline.pipeline_id)
        self.assertTrue(pipeline.has_finalized)
        counter.refresh_from_db()
        self.assertEqual(0, counter.count)

    def test_mapping_over_queryset(self):
        counter = Counter.objects.create()

        pipeline = map_queryset(
            TestModel.objects.all(),
            count,
            finalize_func=delete,
            counter_id=counter.pk
        )

        self.process_task_queues()
        pipeline = get_pipeline_by_id(pipeline.pipeline_id)
        self.assertTrue(pipeline.has_finalized)
        counter.refresh_from_db()

        self.assertEqual(5, counter.count)
        self.assertFalse(TestModel.objects.count())

    def test_slicing(self):
        counter = Counter.objects.create()

        pipeline = map_queryset(
            TestModel.objects.all(),
            slow_count,
            finalize_func=delete,
            counter_id=counter.pk,
            # mapreduce default slice duration is 15 seconds
            # slow down processing enough to split into two slices
            sleep_duration=4,
            _shards=1
        )

        self.process_task_queues()
        pipeline = get_pipeline_by_id(pipeline.pipeline_id)
        self.assertTrue(pipeline.has_finalized)
        counter.refresh_from_db()

        self.assertEqual(5, counter.count)
        self.assertFalse(TestModel.objects.count())

    def test_filters_apply(self):
        counter = Counter.objects.create()

        pipeline = map_queryset(
            TestModel.objects.filter(pk__gt=2),
            count,
            finalize_func=delete,
            counter_id=counter.pk
        )

        self.process_task_queues()
        pipeline = get_pipeline_by_id(pipeline.pipeline_id)
        self.assertTrue(pipeline.has_finalized)
        counter.refresh_from_db()

        self.assertEqual(3, counter.count)
        self.assertFalse(TestModel.objects.count())

    def test_no_start_pipeline(self):
        counter = Counter.objects.create()

        pipeline = map_queryset(
            TestModel.objects.all(),
            count,
            counter_id=counter.pk,
            start_pipeline=False
        )

        self.assertIsNone(pipeline._pipeline_key)

@skipIf(not has_cloudstorage, "Cloud Storage not available")
class MapFilesTests(TestCase):
    @override_settings(CLOUD_STORAGE_BUCKET='test_bucket')
    def test_map_over_files(self):
        storage = CloudStorage()
        storage.save('a/b/c/tmp1', ContentFile('abcdefghi'))
        storage.save('c/tmp2', ContentFile('not matching pattern'))
        storage.save('a/d/tmp3', ContentFile('xxx'))

        counter = Counter.objects.create()
        pipeline = map_files(
            'test_bucket',
            count_contents,
            filenames=['a/*'],
            counter_id=counter.pk
        )

        self.process_task_queues()
        pipeline = get_pipeline_by_id(pipeline.pipeline_id)
        self.assertTrue(pipeline.has_finalized)
        counter.refresh_from_db()
        self.assertEqual(12, counter.count)


def count_entity(entity, counter_id):
    assert isinstance(entity, datastore.Entity)

    counter = Counter.objects.get(pk=counter_id)
    counter.count = models.F('count') + 1
    counter.save()


class MapEntitiesTests(TestCase):
    def setUp(self):
        for i in range(5):
            TestModel.objects.create(id=i+1, text=str(i))

    def test_filters(self):
        counter = Counter.objects.create()

        pipeline = map_entities(
            TestModel._meta.db_table,
            connection.settings_dict['NAMESPACE'],
            count_entity,
            finalize_func=delete,
            counter_id=counter.pk,
            _filters=[("text", "=", "3")]
        )

        self.process_task_queues()
        pipeline = get_pipeline_by_id(pipeline.pipeline_id)
        self.assertTrue(pipeline.has_finalized)
        counter.refresh_from_db()

        self.assertEqual(1, counter.count)
        self.assertFalse(TestModel.objects.count())

    def test_mapping_over_entities(self):
        counter = Counter.objects.create()

        pipeline = map_entities(
            TestModel._meta.db_table,
            connection.settings_dict['NAMESPACE'],
            count_entity,
            finalize_func=delete,
            counter_id=counter.pk
        )

        self.process_task_queues()
        pipeline = get_pipeline_by_id(pipeline.pipeline_id)
        self.assertTrue(pipeline.has_finalized)
        counter.refresh_from_db()

        self.assertEqual(5, counter.count)
        self.assertFalse(TestModel.objects.count())
