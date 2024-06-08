import os, sys
from django.urls import resolve

from givefood.const.general import ENABLE_WRITE

def context(request):

    context = {
        'canonical_path': "https://www.givefood.org.uk%s" % (request.path),
        'instance_id': os.environ.get('GAE_INSTANCE'),
        'version': os.environ.get('GAE_VERSION'),
        'enable_write':ENABLE_WRITE,
        'app_name': sys.modules[resolve(request.path_info).func.__module__].__package__,
    }

    return context
