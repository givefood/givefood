def context(request):

    context = {
        'CANONICAL_PATH': "https://www.givefood.org.uk%s" % (request.path),
    }

    return context
