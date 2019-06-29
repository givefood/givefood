""" Utilities for caching PKs of recently created/modified objects. """

# STANDARD LIB
import datetime

# 3RD PARTY
from djangae.contrib.common import get_request
from django.core.cache import cache
from django.utils import timezone


def get_caches(names):
    """ Given a list of cache names, e.g. ["django", "session"] return the classes that implement them. """
    return [CACHES[x] for x in names]


"""
Each class should implement an `add` and `remove` method, which should both take args of `obj`,
`config` and `cache_key`.
The `get_pks` method takes a `model_class` and `cache_key` should return all PKs in the cache.
In all cases the `cache_key` doesn't have to be used but is passed for convenience and efficiency.
"""


class DjangoCache(object):
    """ Uses django.core.cache to cache objects. """

    def add(self, obj, config, cache_key):
        cache_time = config["cache_time"]
        objects = cache.get(cache_key) or {}
        # take the opportunity to prune our cache of any objects which were created a while
        # ago and should therefore now be being returned by the Datastore
        objects = strip_old_objects(objects, cache_time)
        objects[obj.pk] = timezone.now()
        cache.set(cache_key, objects, cache_time)

    def remove(self, obj, config, cache_key):
        objects = cache.get(cache_key) or {}
        # take the opportunity to prune our cache of any objects which were created a while
        # ago and should therefore now be being returned by the Datastore
        updated_objects = strip_old_objects(objects, config["cache_time"])
        try:
            del updated_objects[obj.pk]
        except KeyError:
            pass
        if updated_objects != objects:
            # only update the cache if it's changed
            cache.set(cache_key, objects) # TODO use check and set to make this transactional

    def get_pks(self, model_class, config, cache_key):
        result = cache.get(cache_key) or {}
        # We strip out any PKs which are older than the cache_time, but for speed
        # we don't bother updating the cache, we only do that when saving an object
        if result:
            result = strip_old_objects(result, config["cache_time"])
        return result.keys()


class SessionCache(object):
    """ Uses request.session to cache objects.  This means that newly created/modified objects are
        only cached for the user who created/modified them.  Potentially a common use case.
        Relies on djangae.contrib.common.get_request to get the request object.
    """

    CONTAINER_KEY = 'CONSISTENCY_CACHES'

    def add(self, obj, config, cache_key):
        request = get_request()
        if request:
            caches_dict = request.session.setdefault(self.CONTAINER_KEY, {})
            model_cache = caches_dict.get(cache_key, {})
            if model_cache:
                model_cache = strip_old_objects(model_cache, config["cache_time"])
            model_cache[obj.pk] = timezone.now()
            caches_dict[cache_key] = model_cache

    def remove(self, obj, config, cache_key):
        request = get_request()
        if request:
            caches_dict = request.session.setdefault(self.CONTAINER_KEY, {})
            model_cache = caches_dict.get(cache_key, {})
            if model_cache:
                model_cache = strip_old_objects(model_cache, config["cache_time"])
                try:
                    del model_cache[obj.pk]
                except KeyError:
                    pass
                caches_dict[cache_key] = model_cache

    def get_pks(self, model_class, config, cache_key):
        request = get_request()
        if request:
            caches_dict = request.session.setdefault(self.CONTAINER_KEY, {})
            model_cache = caches_dict.get(cache_key, {})
            # We strip out any PKs which are older than the cache_time, but for speed
            # we don't bother updating the cache, we only do that when saving an object
            if model_cache:
                model_cache = strip_old_objects(model_cache, config["cache_time"])
            return model_cache.keys()
        return []


def strip_old_objects(objects, max_age):
    to_keep = {}
    threshold = timezone.now() - datetime.timedelta(seconds=max_age)
    for obj_pk, created_time in objects.iteritems():
        if created_time >= threshold:
            # object is still new enough to keep in the cache
            to_keep[obj_pk] = created_time
    return to_keep


CACHES = {"django": DjangoCache(), "session": SessionCache()}
