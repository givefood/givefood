import __builtin__
import functools
import json
import logging
import yaml

from google.appengine.api import urlfetch

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

class ApiSecurityException(Exception):
    """Error when attempting to call an unsafe API."""
    pass


def find_argument_index(function, argument):
    args = function.func_code.co_varnames[:function.func_code.co_argcount]
    return args.index(argument)


def get_default_argument(function, argument):
    argument_index = find_argument_index(function, argument)
    num_positional_args = (function.func_code.co_argcount - len(function.func_defaults))
    default_position = argument_index - num_positional_args
    if default_position < 0:
        return None
    return function.func_defaults[default_position]


def replace_default_argument(function, argument, replacement):
    argument_index = find_argument_index(function, argument)
    num_positional_args = (function.func_code.co_argcount -
                         len(function.func_defaults))
    default_position = argument_index - num_positional_args
    if default_position < 0:
        raise ApiSecurityException('Attempt to modify positional default value')
    new_defaults = list(function.func_defaults)
    new_defaults[default_position] = replacement
    function.func_defaults = tuple(new_defaults)


# JSON.
_JSON_CHARACTER_REPLACEMENT_MAPPING = [
    ('<', '\\u%04x' % ord('<')),
    ('>', '\\u%04x' % ord('>')),
    ('&', '\\u%04x' % ord('&')),
]


class _JsonEncoderForHtml(json.JSONEncoder):
    def encode(self, o):
        chunks = self.iterencode(o, _one_shot=True)
        if not isinstance(chunks, (list, tuple)):
            chunks = list(chunks)
        return ''.join(chunks)

    def iterencode(self, o, _one_shot=False):
        chunks = super(_JsonEncoderForHtml, self).iterencode(o, _one_shot)
        for chunk in chunks:
            for (character, replacement) in _JSON_CHARACTER_REPLACEMENT_MAPPING:
                chunk = chunk.replace(character, replacement)
            yield chunk

def _HttpUrlLoggingWrapper(func):
    """Decorates func, logging when 'url' params do not start with https://."""
    @functools.wraps(func)
    def _CheckAndLog(*args, **kwargs):
        try:
            arg_index = find_argument_index(func, 'url')
        except ValueError:
            return func(*args, **kwargs)

        if arg_index < len(args):
            arg_value = args[arg_index]
        elif 'url' in kwargs:
            arg_value = kwargs['url']
        elif 'url' not in kwargs:
            arg_value = get_default_argument(func, 'url')

        if arg_value and not arg_value.startswith('https://'):
            logging.warn('SECURITY : fetching non-HTTPS url %r', arg_value)
        return func(*args, **kwargs)
    return _CheckAndLog

PATCHES_APPLIED = False

class AppEngineSecurityMiddleware(object):
    """
        This middleware patches over some more insecure parts of the Python and AppEngine libraries.

        The patches are taken from here: https://github.com/google/gae-secure-scaffold-python

        You should add this middleware first in your middleware classes
    """

    def __init__(self, *args, **kwargs):
        global PATCHES_APPLIED
        if not PATCHES_APPLIED:
            # json module does not escape HTML metacharacters by default.
            replace_default_argument(json.dump, 'cls', _JsonEncoderForHtml)
            replace_default_argument(json.dumps, 'cls', _JsonEncoderForHtml)

            # YAML.  The Python tag scheme allows arbitrary code execution:
            # yaml.load('!!python/object/apply:os.system ["ls"]')
            replace_default_argument(yaml.compose, 'Loader', yaml.loader.SafeLoader)
            replace_default_argument(yaml.compose_all, 'Loader', yaml.loader.SafeLoader)
            replace_default_argument(yaml.load, 'Loader', yaml.loader.SafeLoader)
            replace_default_argument(yaml.load_all, 'Loader', yaml.loader.SafeLoader)
            replace_default_argument(yaml.parse, 'Loader', yaml.loader.SafeLoader)
            replace_default_argument(yaml.scan, 'Loader', yaml.loader.SafeLoader)

            # AppEngine urlfetch.
            # Does not validate certificates by default.
            replace_default_argument(urlfetch.fetch, 'validate_certificate', True)
            replace_default_argument(urlfetch.make_fetch_call, 'validate_certificate', True)
            urlfetch.fetch = _HttpUrlLoggingWrapper(urlfetch.fetch)
            urlfetch.make_fetch_call = _HttpUrlLoggingWrapper(urlfetch.make_fetch_call)

            for setting in ("CSRF_COOKIE_SECURE", "SESSION_COOKIE_HTTPONLY", "SESSION_COOKIE_SECURE"):
                if not getattr(settings, setting, False):
                    logging.warning("settings.%s is not set to True, this is insecure", setting)

            PATCHES_APPLIED = True
        raise MiddlewareNotUsed()
