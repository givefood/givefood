import os
import re
import sys
import argparse

import djangae.sandbox as sandbox
from djangae import environment

# Set some Django-y defaults
DJANGO_DEFAULTS = {
    "storage_path": os.path.join(environment.get_application_root(), ".storage"),
    "port": 8000,
    "admin_port": 8001,
    "api_port": 8002,
    "automatic_restart": "True",
    "allow_skipped_files": "True",
}


def _execute_from_command_line(sandbox_name, argv, **sandbox_overrides):
    # Parses for a settings flag, adding it as an environment variable to
    # the sandbox if found.
    parser = argparse.ArgumentParser(prog='manage.py')
    parser.add_argument('--settings', nargs='?')
    parsed = parser.parse_known_args(argv)
    settings = parsed[0].settings
    env_vars = {}
    if settings:
        env_vars['DJANGO_SETTINGS_MODULE'] = settings

    # retrieve additional overridden module settings
    for arg in parsed[1]:
        m = re.match(r'--(?P<module_name>.+)-settings=(?P<settings_path>.+)', arg)
        if m:
            argv.remove(arg)
            env_vars['%s_DJANGO_SETTINGS_MODULE' % m.group('module_name')] = m.group('settings_path')

    with sandbox.activate(
        sandbox_name,
        add_sdk_to_path=True,
        new_env_vars=env_vars,
        **sandbox_overrides
    ):
        import django.core.management as django_management  # Now on the path
        return django_management.execute_from_command_line(argv)


def execute_from_command_line(argv=None, **sandbox_overrides):
    """Wraps Django's `execute_from_command_line` to initialize a djangae
    sandbox before running a management command.

    Note: The '--sandbox' arg must come first. All other args are forwarded to
          Django as normal.
    """
    argv = argv or sys.argv
    parser = argparse.ArgumentParser(prog='manage.py')
    parser.add_argument(
        '--sandbox', default=sandbox.LOCAL, choices=sandbox.SANDBOXES.keys())
    parser.add_argument('args', nargs=argparse.REMAINDER)
    namespace = parser.parse_args(argv[1:])

    overrides = DJANGO_DEFAULTS
    overrides.update(sandbox_overrides)

    return _execute_from_command_line(namespace.sandbox, ['manage.py'] + namespace.args, **overrides)


def remote_execute_from_command_line(argv=None, **sandbox_overrides):
    """Execute commands in the remote sandbox"""
    return _execute_from_command_line(sandbox.REMOTE, argv or sys.argv, **sandbox_overrides)


def local_execute_from_command_line(argv=None, **sandbox_overrides):
    """Execute commands in the local sandbox"""
    return _execute_from_command_line(sandbox.LOCAL, argv or sys.argv, **sandbox_overrides)


def test_execute_from_command_line(argv=None, **sandbox_overrides):
    """Execute commands in the test sandbox"""
    return _execute_from_command_line(sandbox.TEST, argv or sys.argv, **sandbox_overrides)
