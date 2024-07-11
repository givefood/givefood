import os, sys
from django.urls import resolve

from givefood.const.general import ENABLE_WRITE, SITE_DOMAIN

def context(request):

    canonical_path = "%s%s" % (SITE_DOMAIN, request.path)
    instance_id = os.environ.get('GAE_INSTANCE')
    version = os.environ.get('GAE_VERSION')
    try:
        app_name = sys.modules[resolve(request.path_info).func.__module__].__package__
    except:
        app_name = "unknown"

    context = {
        'canonical_path': canonical_path,
        'instance_id': instance_id,
        'version': version,
        'enable_write': ENABLE_WRITE,
        'app_name': app_name,
    }

    return context
