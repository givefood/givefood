from djangae.contrib.common import _thread_locals


class RequestStorageMiddleware:
    """ Middleware which allows us to get hold of the request object in places where Django doesn't give it to us, e.g. in model save methods.
        Use get_request() to access the request object.
    """

    def process_request(self, request):
        _thread_locals.request = request

    def process_response(self, request, response):
        # Wipe out the request so that if the following request to this instance doesn't call the middleware (e.g. deferred tasks) we don't end up with randomness
        _thread_locals.request = None
        return response

    def process_exception(self, request, exception):
        _thread_locals.request = None
        return None  # Allow default exception handling to take over
