try:
    from google.appengine.tools.devappserver2.python import sandbox
except ImportError:
    from google.appengine.tools.devappserver2.python.runtime import sandbox

try:
    from google.appengine.tools.devappserver2.python import runtime
except ImportError:
    from google.appengine.tools.devappserver2.python.runtime import runtime

try:
    from google.appengine.tools.devappserver2.constants import LOG_LEVEL_TO_RUNTIME_CONSTANT
    _LOG_LEVEL_TO_RUNTIME_CONSTANT = LOG_LEVEL_TO_RUNTIME_CONSTANT
except ImportError:
    from google.appengine.tools.devappserver2.devappserver2 import _LOG_LEVEL_TO_RUNTIME_CONSTANT
