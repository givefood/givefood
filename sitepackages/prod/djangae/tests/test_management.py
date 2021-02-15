# LIBRARIES
from contextlib import contextmanager

# DJANGAE
from djangae.contrib import sleuth
from djangae.core.management import execute_from_command_line
from djangae.test import TestCase


@contextmanager
def test_context_manager(*args, **kwargs):
    yield

class ManagementCommandsTest(TestCase):
    def test_arguments_are_passed_through_correctly(self):
        with sleuth.switch("django.core.management.execute_from_command_line", lambda *args, **kwargs: None) as django_execute_mock, \
             sleuth.switch("djangae.sandbox.activate", test_context_manager):
            execute_from_command_line(['manage.py', 'arg1', 'arg2', 'arg3',])
            self.assertEqual(1, django_execute_mock.call_count)
            self.assertEqual((['manage.py', 'arg1', 'arg2', 'arg3',],), django_execute_mock.calls[0].args)

    def test_sandbox_can_be_specified(self):
        with sleuth.switch("django.core.management.execute_from_command_line", lambda *args, **kwargs: None) as django_execute_mock, \
             sleuth.switch("djangae.sandbox.activate", test_context_manager) as activate_sandbox_mock:

            # test default sandbox is used if no sandbox argument
            execute_from_command_line(['manage.py', 'arg1', 'arg2',])
            self.assertEqual(1, activate_sandbox_mock.call_count)
            self.assertEqual('local', activate_sandbox_mock.calls[0].args[0])
            self.assertEqual(1, django_execute_mock.call_count)
            self.assertEqual((['manage.py', 'arg1', 'arg2',],), django_execute_mock.calls[0].args)

            # test that sandbox argument is used when given
            execute_from_command_line(['manage.py', '--sandbox=test', 'arg1', 'arg2',])
            self.assertEqual(2, activate_sandbox_mock.call_count)
            self.assertEqual('test', activate_sandbox_mock.calls[1].args[0])
            self.assertEqual(2, django_execute_mock.call_count)
            self.assertEqual((['manage.py', 'arg1', 'arg2',],), django_execute_mock.calls[1].args)

            # test that sandbox argument can be in any position
            execute_from_command_line(['manage.py', 'arg1', '--sandbox=test', 'arg2',])
            self.assertEqual(3, activate_sandbox_mock.call_count)
            self.assertEqual('test', activate_sandbox_mock.calls[2].args[0])
            self.assertEqual(3, django_execute_mock.call_count)
            self.assertEqual((['manage.py', 'arg1', 'arg2',],), django_execute_mock.calls[2].args)
