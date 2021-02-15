
import django.dispatch

from google.appengine.api.datastore import MAX_ALLOWABLE_QUERIES  # noqa
from google.appengine.api.datastore import Delete as _Delete
from google.appengine.api.datastore import DeleteAsync as _DeleteAsync
from google.appengine.api.datastore import Entity  # noqa
from google.appengine.api.datastore import Get as _Get
from google.appengine.api.datastore import (IsInTransaction, Key,   # noqa
                                            NonTransactional)
from google.appengine.api.datastore import Put as _Put
from google.appengine.api.datastore import PutAsync as _PutAsync
from google.appengine.api.datastore import Query, RunInTransaction  # noqa


# This signal exists mainly so the atomic decorator can find out what's happened
datastore_get = django.dispatch.Signal(providing_args=["keys"])
datastore_post_put = django.dispatch.Signal(providing_args=["keys"])


def Get(keys, **kwargs):
    datastore_get.send(sender=Get, keys=keys if isinstance(keys, (list, tuple)) else [keys])
    return _Get(keys, **kwargs)


def Put(*args, **kwargs):
    result = _Put(*args, **kwargs)
    datastore_post_put.send(sender=Put, keys=[result] if isinstance(result, Key) else result)
    return _Put(*args, **kwargs)


def PutAsync(*args, **kwargs):
    return _PutAsync(*args, **kwargs)


def Delete(*args, **kwargs):
    return _Delete(*args, **kwargs)


def DeleteAsync(*args, **kwargs):
    return _DeleteAsync(*args, **kwargs)
