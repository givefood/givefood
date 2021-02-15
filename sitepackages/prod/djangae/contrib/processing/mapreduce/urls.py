from django.conf.urls import url
from djangae.utils import djangae_webapp

from django.views.decorators.csrf import csrf_exempt

# The Mapreduce status UI uses inline JS, which will fail If we have django-csp
# installed and are not allowing 'unsafe-inline' as a SCRIPT_SRC.
try:
    from csp.decorators import csp_update
    exempt_from_unsafe_inline = csp_update(SCRIPT_SRC=("'unsafe-inline'",))
except ImportError:
    exempt_from_unsafe_inline = lambda func: func


try:
    from mapreduce.main import create_handlers_map
    wrapped_urls = [
        url(
            url_re.replace('.*/', '^', 1),
            exempt_from_unsafe_inline(csrf_exempt(djangae_webapp(func)))
        )
        for url_re, func in create_handlers_map()
    ]
except ImportError as e:
    wrapped_urls = []


urlpatterns = wrapped_urls
