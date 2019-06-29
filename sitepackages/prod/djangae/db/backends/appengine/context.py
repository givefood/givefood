import copy
import collections

from google.appengine.api import datastore

class CopyDict(collections.MutableMapping):
    """
        It's important we don't pass references around in and out
        of the cache, so this just ensures we copy stuff going in, and
        copy it going out!
    """
    def __init__(self, *args, **kwargs):
        self._store = {}
        super(CopyDict, self).__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        value = copy.deepcopy(value)
        self._store[key] = value

    def __getitem__(self, key):
        value = self._store[key]
        return copy.deepcopy(value)

    def __delitem__(self, key):
        del self._store[key]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)


class ContextCache(object):
    """ Object via which the stack of Context objects and the settings for the context caching are
        accessed. A separate instance of this should exist per thread.
    """
    def __init__(self):
        self.memcache_enabled = True
        self.context_enabled = True
        self.stack = ContextStack()

    def reset(self, keep_disabled_flags=False):
        if datastore.IsInTransaction():
            raise RuntimeError(
                "Clearing the context cache inside a transaction breaks everything, "
                "we can't let you do that"
            )
        self.stack = ContextStack()
        if not keep_disabled_flags:
            self.memcache_enabled = True
            self.context_enabled = True


class Context(object):

    def __init__(self, stack):
        self.cache = CopyDict()
        self.reverse_cache = CopyDict()
        self._stack = stack

    def apply(self, other):
        self.cache.update(other.cache)

        # We have to delete things that don't exist in the other
        for k in self.cache.keys():
            if k not in other.cache:
                del self.cache[k]

        self.reverse_cache.update(other.reverse_cache)

        # We have to delete things that don't exist in the other
        for k in self.reverse_cache.keys():
            if k not in other.reverse_cache:
                del self.reverse_cache[k]

    def cache_entity(self, identifiers, entity, situation):
        assert hasattr(identifiers, "__iter__")

        for identifier in identifiers:
            self.cache[identifier] = copy.deepcopy(entity)

        self.reverse_cache[entity.key()] = identifiers

    def remove_entity(self, entity_or_key):
        if not isinstance(entity_or_key, datastore.Key):
            entity_or_key = entity_or_key.key()

        for identifier in self.reverse_cache[entity_or_key]:
            del self.cache[identifier]

        del self.reverse_cache[entity_or_key]

    def get_entity(self, identifier):
        return self.cache.get(identifier)

    def get_entity_by_key(self, key):
        try:
            identifier = self.reverse_cache[key][0]
        except KeyError:
            return None
        return self.get_entity(identifier)


class ContextStack(object):
    """
        A stack of contexts. This is used to support in-context
        caches for multi level transactions.
    """

    def __init__(self):
        self.stack = [ Context(self) ]
        self.staged = []

    def push(self):
        self.stack.append(
            Context(self) # Empty context
        )

    def pop(self, apply_staged=False, clear_staged=False, discard=False):
        """
            apply_staged: pop normally takes the top of the stack and adds it to a FIFO
            queue. By passing apply_staged it will pop to the FIFO queue then apply the
            queue to the top of the stack.

            clear_staged: pop, and then wipe out any staged contexts.

            discard: Ignores the popped entry in the stack, it's just discarded

            The staged queue will be wiped out if the pop makes the size of the stack one,
            regardless of whether you pass clear_staged or not. This is for safety!
        """
        from . import caching


        if not discard:
            self.staged.insert(0, self.stack.pop())
        else:
            self.stack.pop()

        if apply_staged:
            while self.staged:
                to_apply = self.staged.pop()
                keys = to_apply.reverse_cache.keys()
                if keys:
                    # This assumes that all keys are in the same namespace, which is almost definitely
                    # going to be the case, but it feels a bit dirty
                    namespace = keys[0].namespace() or None
                    caching.remove_entities_from_cache_by_key(
                        keys, namespace=namespace, memcache_only=True
                    )

                self.top.apply(to_apply)

        if clear_staged or len(self.stack) == 1:
            self.staged = []

    @property
    def top(self):
        return self.stack[-1]

    @property
    def size(self):
        return len(self.stack)

    @property
    def staged_count(self):
        return len(self.staged)
