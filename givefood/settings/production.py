
from .default import *

ALLOWED_HOSTS = [
    '.appspot.com',
    '.givefood.org.uk',
]

# Disable DEBUG on production
DEBUG = False

# Strip out middleware only designed for local development
_LOCAL_ONLY_MIDDLEWARE = (
    'djangae.contrib.googleauth.middleware.LocalIAPLoginMiddleware',
)

MIDDLEWARE = [
    x for x in MIDDLEWARE
    if x not in _LOCAL_ONLY_MIDDLEWARE
]


# Enable secure settings

SESSION_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 2592000 #30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_SSL_REDIRECT = True

SECURE_REDIRECT_EXEMPT = [
    # App Engine doesn't use HTTPS internally, so the /_ah/.* URLs need to be exempt.
    # Django compares these to request.path.lstrip("/"), hence the lack of preceding /
    r"^_ah/",
    r"^offline/",
]

# CSP Configuration

CSP_REPORT_ONLY = False


# Un-comment if using cache with Cloud Memory Store memcache. For LOCATION use
# the 'Discovery endpoint' value for the instance.
#CACHES = {
#    "default": {
#        "BACKEND": "django.core.cache.backends.memcached.MemcachedCache",
#        "LOCATION": "x.x.x.x:11211",
#    }
#}
