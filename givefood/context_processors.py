import os

def context(request):

    context = {
        'canonical_path': "https://www.givefood.org.uk%s" % (request.path),
        'instance_id': os.environ.get('GAE_INSTANCE'),
        'version': os.environ.get('GAE_VERSION'),
    }

    return context
