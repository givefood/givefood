from __future__ import absolute_import

import logging

from django.db import models
from django.utils.six.moves import range

from djangae.test import TestCase
from djangae.test import process_task_queues

from mapreduce import pipeline_base

# from mapreduce import mapreduce_pipeline


class TestNode(models.Model):
    data = models.CharField(max_length=32)
    counter = models.IntegerField()

    class Meta:
        app_label = "mapreduce"


class LogResult(pipeline_base.PipelineBase):

    def run(self, number):
        logging.info('All done! Value is %s', number)


class IncrementPipeline(pipeline_base.PipelineBase):
    def run(self, *args, **kwargs):
        node = TestNode.objects.get()
        node.counter += 1
        node.save()


class SquareOutputPipeline(pipeline_base.PipelineBase):

    output_names = ['square']

    def run(self, number):
        self.fill(self.outputs.square, number * number)

    def finalized(self):
        logging.info('All done! Square is %s', self.outputs.square.value)


class SquarePipeline(pipeline_base.PipelineBase):

    def run(self, number):
        logging.info('Squaring: %s' % number)
        return number * number


class Sum(pipeline_base.PipelineBase):

    def run(self, *args):
        value = sum(list(args))
        logging.info('Sum: %s', value)
        return value


class FanOutFanInPipeline(pipeline_base.PipelineBase):

    def run(self, count):
        results = []
        for i in range(0, count):
            result = yield SquarePipeline(i)
            results.append(result)

        yield Sum(*results)


class PipelineTestCase(TestCase):

    def setUp(self):
        self.testnode = TestNode()
        self.testnode.data = 'Lol'
        self.testnode.counter = 1
        self.testnode.save()
        super(PipelineTestCase, self).setUp()

    def test_model_touch(self):
        """
            Tests that the django context is available inside the pipeline
            run() method
        """
        logging.info('Launching pipeline')
        pipeline = IncrementPipeline()
        pipeline.start()
        process_task_queues()
        node = TestNode.objects.get(pk=self.testnode.pk)
        self.assertEqual(node.counter, self.testnode.counter + 1)


    def test_pipeline_chain(self):
        """
            Tests a more complicated FanOutFanIn chain
        """
        stage = FanOutFanInPipeline(10)
        stage.start()
        process_task_queues()
