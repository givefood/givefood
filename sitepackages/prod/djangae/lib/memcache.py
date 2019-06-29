from google.appengine.api.memcache import *


def set_wrapper(func):
    """
        Apparently App Engine's memcache.set can't deal with a negative time, but some Django
        session tests do this intentionally, so we just wrap set to ignore calls with a negative
        time
    """
    def _wrapped(self, key, value, time=0, min_compress_len=0, namespace=None):
        if time < 0:
            return False

        return func(self, key, value, time, min_compress_len, namespace)

    return _wrapped

Client.set = set_wrapper(Client.set)
