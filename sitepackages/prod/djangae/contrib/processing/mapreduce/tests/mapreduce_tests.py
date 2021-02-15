from __future__ import absolute_import

from mapreduce.mapreduce_pipeline import MapreducePipeline

from django.db import models
from djangae.test import TestCase
from djangae.test import process_task_queues
from djangae.contrib.processing.mapreduce.helpers import DjangoInputReader
from djangae.contrib.processing.mapreduce.utils import qualname
# from djangae.contrib.processing.mapreduce.pipelines import MapPipeline


class MRTestNode(models.Model):
    data = models.CharField(max_length=32)
    counter = models.IntegerField()

    class Meta:
        app_label = "mapreduce"


# class MapPipelineTestCase(TestCase):
#
#     def setUp(self):
#         for x in range(100):
#             self.testnode = TestNode()
#             self.testnode.data = 'Lol'
#             self.testnode.counter = 1
#             self.testnode.save()
#         super(MapPipelineTestCase, self).setUp()
#
#     def test_map_works(self):
#         pipe = MapPipeline(
#             "increment",
#             "djangae.contrib.processing.mapreduce.tests.mapreduce.model_counter_increment",
#             "djangae.contrib.processing.mapreduce.input_readers.DjangoInputReader",
#             mapper_params={'input_reader': {'model': 'mapreduce.TestNode'}},
#             shards=10
#         )
#         pipe.start()
#         process_task_queues()
#         nodes = TestNode.objects.all()
#         for node in nodes:
#             self.assertEqual(node.counter, 2)
#

class DjangoInputReaderTestCase(TestCase):
    ENTITY_COUNT = 300

    def setUp(self):
        for x in range(self.ENTITY_COUNT):
            self.testnode = MRTestNode()
            self.testnode.data = 'Lol'
            self.testnode.counter = 1
            if x < self.ENTITY_COUNT / 4:
                self.testnode.id = x + 1
            self.testnode.save()
        super(DjangoInputReaderTestCase, self).setUp()

    def _test_split_input_on_n_shards(self, shards):
        from mapreduce.model import MapperSpec
        mapper_spec = MapperSpec(
            '',
            '',
            {
                'input_reader': {
                    'model': 'mapreduce.MRTestNode'
                }
            },
            shards,
        )
        readers = DjangoInputReader.split_input(mapper_spec)
        self.assertEqual(len(readers), shards)
        models = []
        for reader in readers:
            for model in reader:
                models.append(model.pk)
        self.assertEqual(len(models), self.ENTITY_COUNT)
        self.assertEqual(len(models), len(set(models)))

    def test_split_input_on_one_shard(self):
        self._test_split_input_on_n_shards(1)

    def test_split_input_on_two_shards(self):
        self._test_split_input_on_n_shards(2)

    def test_split_input_one_batch_per_shard(self):
        self._test_split_input_on_n_shards(6)

class MapreduceTestCase(TestCase):

    def setUp(self):
        for x in range(20):
            self.testnode = MRTestNode()
            self.testnode.data = 'Lol'
            self.testnode.counter = 1
            self.testnode.save()
        super(MapreduceTestCase, self).setUp()

    def test_mapreduce_basic(self):
        """
            Tests basic mapreduce with random input
        """
        pipe = MapreducePipeline(
            "word_count",
            qualname(letter_count_map),
            qualname(word_count_reduce),
            "mapreduce.input_readers.RandomStringInputReader",
            "mapreduce.output_writers.GoogleCloudStorageOutputWriter",
            mapper_params={'count': 10},
            reducer_params={"mime_type": "text/plain", 'output_writer': {'bucket_name': 'test'}},
            shards=1
        )
        pipe.start()
        process_task_queues()

    def test_mapreduce_django_input(self):
        """
            Test basic django operations inside a map task, this shows that
            our handlers are working
        """
        nodes = MRTestNode.objects.all()
        for node in nodes:
            self.assertEqual(node.counter, 1)
        pipe = MapreducePipeline(
            "word_count",
            qualname(model_counter_increment),
            qualname(word_count_reduce),
            "djangae.contrib.processing.mapreduce.input_readers.DjangoInputReader",
            "mapreduce.output_writers.GoogleCloudStorageOutputWriter",
            mapper_params={'count': 10, 'input_reader': {'model': 'mapreduce.MRTestNode'}},
            reducer_params={"mime_type": "text/plain", 'output_writer': {'bucket_name': 'test'}},
            shards=5
        )
        pipe.start()
        process_task_queues()
        nodes = MRTestNode.objects.all()
        for node in nodes:
            self.assertEqual(node.counter, 2)


def letter_count_map(data):
    """Word Count map function."""
    letters = [x for x in data]
    for l in letters:
        yield (l, "")

def model_counter_increment(instance):
    """Word Count map function."""
    instance.counter += 1
    instance.save()
    yield (instance.pk, "{0}".format(instance.counter))

def word_count_reduce(key, values):
    """Word Count reduce function."""
    yield "%s: %d\n" % (key, len(values))
