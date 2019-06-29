# STANDARD LIB
from functools import wraps

# LIBRARIES
from django.conf import settings
from django.test.utils import override_settings


def without_security_middleware(func):
    """ Decorator for disabling djangae.contrib.security.middleware.AppEngineSecurityMiddleware.
    """
    # This is sometimes useful in tests because if you patch something which is patched by the
    # middleware then usually the test patch is applied first, THEN the middleware runs (usually
    # as the result of a self.client.get/post call), thus applying a decorator to the patched
    # function.  The decorator's nested function stores a reference to the original (patched)
    # function, and so when the patch in the test is undone it is actually still being used because
    # the decorator in the middleware is still referencing it.  This decorator is for
    # use in tests where you are patching one of the things which is patched in the middleware,
    # thus allowing you to avoid the afore-described issue.
    middleware = list(settings.MIDDLEWARE_CLASSES[:])
    middleware.remove('djangae.contrib.security.middleware.AppEngineSecurityMiddleware')
    @wraps(func)
    def _wrapped(*args, **kwargs):
        with override_settings(MIDDLEWARE_CLASSES=middleware):
            return func(*args, **kwargs)
    return _wrapped
