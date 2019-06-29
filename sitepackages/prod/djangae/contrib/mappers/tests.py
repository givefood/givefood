import logging

from django.db import models

from djangae.test import TestCase
from djangae.test import process_task_queues
from djangae.contrib.mappers.pipes import MapReduceTask
from djangae.contrib.mappers.defer import defer_iteration, _shard


class TestNode(models.Model):
    data = models.CharField(max_length=32)
    counter = models.IntegerField()


class TestNode2(models.Model):
    data = models.CharField(max_length=32)
    counter = models.IntegerField()


class TestMapperClass(MapReduceTask):

    model = TestNode
    name = 'test_map'

    @staticmethod
    def finish(**kwargs):
        logging.info('TestMapper1 Finished')

    @staticmethod
    def map(entity, *args, **kwargs):
        if entity.counter % 2:
            entity.delete()
            yield ('removed', [entity.pk])
        else:
            yield ('remains', [entity.pk])


class TestMapperClass2(MapReduceTask):

    model = TestNode
    name = 'test_map_2'

    @staticmethod
    def finish(**kwargs):
        logging.info('TestMapper2 Finished')

    @staticmethod
    def map(entity, *args, **kwargs):
        entity.data = "hit"
        entity.save()

class TestMapperClass3(MapReduceTask):

    model = TestNode
    name = 'test_map_3'

    @staticmethod
    def map(entity, *args, **kwargs):
        if all((x in args for x in ['arg1', 'arg2'])) and 'test' in kwargs:
            entity.delete()


class MapReduceTestCase(TestCase):

    def setUp(self):
        super(MapReduceTestCase, self).setUp()

        for x in xrange(10):
            TestNode(data="TestNode".format(x), counter=x).save()

    def test_all_models_delete(self):
        self.assertEqual(TestNode.objects.count(), 10)
        TestMapperClass().start()
        process_task_queues()
        self.assertEqual(TestNode.objects.count(), 5)

    def test_model_init(self):
        """
            Test that overriding the model works
        """
        for x in xrange(10):
            TestNode2(data="TestNode2".format(x), counter=x).save()
        self.assertEqual(TestNode2.objects.count(), 10)
        TestMapperClass(model=TestNode2).start()
        process_task_queues()
        self.assertEqual(TestNode2.objects.count(), 5)

    def test_model_args_kwargs(self):
        """
            Test that overriding the model works
        """
        self.assertEqual(TestNode.objects.count(), 10)
        TestMapperClass3(model=TestNode).start('arg1', 'arg2', test='yes')
        process_task_queues()
        self.assertEqual(TestNode.objects.count(), 0)

    def test_map_fruit_update(self):
        self.assertEqual(TestNode.objects.count(), 10)
        TestMapperClass2().start()
        process_task_queues()
        nodes = TestNode.objects.all()
        self.assertTrue(all(x.data == 'hit' for x in nodes))

def zero_count(node):
    node.counter = 0
    node.save()


def add_onehundred(node):
    node.counter += 100
    node.save()


class TestDeferIteration(TestCase):
    def setUp(self):
        super(TestDeferIteration, self).setUp()

        for x in xrange(10):
            TestNode.objects.create(data="TestNode {}".format(x), counter=x+1)

    def test_that_sharding_works(self):
        _shard(
            TestNode,
            TestNode.objects.all().query,
            zero_count,
            shard_size=1,
            queue="default"
        )

        self.assertNumTasksEquals(10)
        self.process_task_queues()
        self.assertEqual(10, TestNode.objects.filter(counter=0).count())

    def test_that_processing_works(self):
        " By adding 100, we can check that everything is called exactly once"

        defer_iteration(TestNode.objects.all(), add_onehundred)

        self.assertTrue(sum(TestNode.objects.values_list("counter", flat=True)))

        self.process_task_queues()

        self.assertEqual(
            sum([(x+1) + 100 for x in xrange(10)]),
            sum(TestNode.objects.values_list("counter", flat=True))
        )
