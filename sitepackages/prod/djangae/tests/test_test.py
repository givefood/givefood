from google.appengine.ext import deferred
from google.appengine.api import taskqueue

from djangae.test import TestCase, _get_queued_tasks, TaskFailedBehaviour, TaskFailedError


def my_task():
    """
    Basic task for testing task queues.
    """
    pass


def throw_once():
    throw_once.counter += 1
    if throw_once.counter == 1:
        raise Exception("First call")


throw_once.counter = 0

class TaskQueueTests(TestCase):

    def test_get_queued_tasks_flush(self):
        deferred.defer(my_task)
        deferred.defer(my_task, _queue='another')

        # We don't use self.assertNumTasksEquals here because we want to flush.
        tasks = _get_queued_tasks(self.taskqueue_stub, queue_name='default')
        self.assertEqual(1, len(tasks))

        tasks = _get_queued_tasks(self.taskqueue_stub, queue_name='another')
        self.assertEqual(1, len(tasks))

        tasks = _get_queued_tasks(self.taskqueue_stub)
        self.assertEqual(0, len(tasks))

    def test_task_queue_processing_control(self):

        deferred.defer(throw_once)

        self.process_task_queues(failure_behaviour=TaskFailedBehaviour.RETRY_TASK)

        # Should've retried
        self.assertEqual(throw_once.counter, 2)

        throw_once.counter = 0

        deferred.defer(throw_once)

        self.assertRaises(
            TaskFailedError,
            self.process_task_queues,
            failure_behaviour=TaskFailedBehaviour.RAISE_ERROR
        )
        self.assertEqual(throw_once.counter, 1)

    def test_pull_task(self):

        queue_name = 'pull'

        taskqueue.Queue(queue_name).add(
            taskqueue.Task(payload='payload', tag='tag', method='PULL')
        )

        # verify pulled task is queued, but don't flush
        tasks = _get_queued_tasks(self.taskqueue_stub, queue_name=queue_name, flush=False)
        self.assertEqual(1, len(tasks))

        # verify pulled task is ignored
        tasks = _get_queued_tasks(self.taskqueue_stub, queue_name=queue_name, process_pull_tasks=False)
        self.assertEqual(0, len(tasks))

        # processing should ignore pull tasks
        self.process_task_queues()

        # pull task should still exist after processing
        tasks = _get_queued_tasks(self.taskqueue_stub, queue_name=queue_name)
        self.assertEqual(1, len(tasks))

        # pull task should be flushed
        tasks = _get_queued_tasks(self.taskqueue_stub, queue_name=queue_name)
        self.assertEqual(0, len(tasks))
