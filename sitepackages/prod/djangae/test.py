import contextlib
import logging
import os

from django import test
from django.test import Client

from djangae.environment import get_application_root

from google.appengine.api import apiproxy_stub_map, appinfo
from google.appengine.datastore import datastore_stub_util
from google.appengine.tools.devappserver2.application_configuration import ModuleConfiguration
from google.appengine.tools.devappserver2.module import _ScriptHandler


@contextlib.contextmanager
def inconsistent_db(probability=0, connection='default'):
    """
        A context manager that allows you to make the datastore inconsistent during testing.
        This is vital for writing applications that deal with the Datastore's eventual consistency
    """

    from django.db import connections

    conn = connections[connection]

    if not hasattr(conn.creation, "testbed") or "datastore_v3" not in conn.creation.testbed._enabled_stubs:
        raise RuntimeError("Tried to use the inconsistent_db stub when not testing")


    stub = apiproxy_stub_map.apiproxy.GetStub('datastore_v3')

    # Set the probability of the datastore stub
    original_policy = stub._consistency_policy
    stub.SetConsistencyPolicy(datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=probability))
    try:
        yield
    finally:
        # Restore to consistent mode
        stub.SetConsistencyPolicy(original_policy)


def _get_queued_tasks(stub, queue_name=None, flush=True):
    tasks = []

    for queue in stub.GetQueues():
        for task in stub.GetTasks(queue['name']):
            if queue_name is None or queue_name == queue['name']:
                tasks.append(task)

        if flush:
            stub.FlushQueue(queue["name"])

    return tasks

def _flush_tasks(stub, queue_name=None):
    if queue_name:
        stub.FlushQueue(queue_name)
    else:
        for queue in stub.GetQueues():
            stub.FlushQueue(queue["name"])

def process_task_queues(queue_name=None):
    """
        Processes any queued tasks inline without a server.
        This is useful for end-to-end testing background tasks.
    """

    stub = apiproxy_stub_map.apiproxy.GetStub("taskqueue")

    tasks = _get_queued_tasks(stub, queue_name)

    client = Client() # Instantiate a test client for processing the tasks

    while tasks:
        task = tasks.pop(0) # Get the first task

        decoded_body = task['body'].decode('base64')
        post_data = decoded_body
        headers = { "HTTP_{}".format(x.replace("-", "_").upper()): y for x, y in task['headers'] }

        #FIXME: set headers like the queue name etc.
        method = task['method']

        if method.upper() == "POST":
            #Fixme: post data?
            response = client.post(task['url'], data=post_data, content_type=headers['HTTP_CONTENT_TYPE'], **headers)
        else:
            response = client.get(task['url'], **headers)

        if response.status_code != 200:
            logging.info("Unexpected status (%r) while simulating task with url: %r", response.status_code, task['url'])

        if not tasks:
            #The map reduce may have added more tasks, so refresh the list
            tasks = _get_queued_tasks(stub, queue_name)


class TestCaseMixin(object):
    def setUp(self):
        super(TestCaseMixin, self).setUp()
        self.taskqueue_stub = apiproxy_stub_map.apiproxy.GetStub("taskqueue")
        if self.taskqueue_stub:
            _flush_tasks(self.taskqueue_stub) # Make sure we clear the queue before every test

    def assertNumTasksEquals(self, num, queue_name='default'):
        self.assertEqual(num, len(_get_queued_tasks(self.taskqueue_stub, queue_name, flush=False)))

    def process_task_queues(self, queue_name=None):
        process_task_queues(queue_name)


class HandlerAssertionsMixin(object):
    """
    Custom assert methods which verifies a range of handler configuration
    setting specified in app.yaml.
    """

    msg_prefix = 'Handler configuration for {url} is not protected by {perm}.'

    def assert_login_admin(self, url):
        """
        Test that the handler defined in app.yaml which matches the url provided
        has `login: admin` in the configuration.
        """
        handler = self._match_handler(url)
        self.assertEqual(
            handler.url_map.login, appinfo.LOGIN_ADMIN, self.msg_prefix.format(
                url=url, perm='`login: admin`'
            )
        )

    def assert_login_required(self, url):
        """
        Test that the handler defined in app.yaml which matches the url provided
        has `login: required` or `login: admin` in the configruation.
        """
        handler = self._match_handler(url)
        login_admin = handler.url_map.login == appinfo.LOGIN_ADMIN
        login_required = handler.url_map.login == appinfo.LOGIN_REQUIRED or login_admin

        self.assertTrue(login_required, self.msg_prefix.format(
                url=url, perm='`login: admin` or `login: required`'
            )
        )

    def _match_handler(self, url):
        """
        Load script handler configurations from app.yaml and try to match
        the provided url path to a url_maps regex.
        """
        app_yaml_path = os.path.join(get_application_root(), "app.yaml")
        config = ModuleConfiguration(app_yaml_path)

        url_maps = config.handlers
        script_handlers = [
            _ScriptHandler(maps) for
            maps in url_maps if
            maps.GetHandlerType() == appinfo.HANDLER_SCRIPT
        ]

        for handler in script_handlers:
            if handler.match(url):
                return handler

        raise AssertionError('No handler found for {url}'.format(url=url))


class TestCase(HandlerAssertionsMixin, TestCaseMixin, test.TestCase):
    pass


class TransactionTestCase(HandlerAssertionsMixin, TestCaseMixin, test.TransactionTestCase):
    pass
