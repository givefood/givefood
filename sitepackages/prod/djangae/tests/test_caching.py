from google.appengine.api import datastore
from google.appengine.api import datastore_errors
from google.appengine.ext.db import non_transactional

from django.db import connection as default_connection, models
from django.http import HttpRequest
from django.core.signals import request_finished, request_started
from django.core.cache import cache

from djangae.contrib import sleuth
from djangae.test import TestCase
from djangae.db import unique_utils
from djangae.db import transaction
from djangae.db.backends.appengine.context import ContextStack
from djangae.db.backends.appengine import caching
from djangae.db.caching import disable_cache


DEFAULT_NAMESPACE = default_connection.ops.connection.settings_dict.get("NAMESPACE")


class FakeEntity(dict):
    COUNTER = 1

    def __init__(self, data, id=0):
        self.id = id or FakeEntity.COUNTER
        FakeEntity.COUNTER += 1
        self.update(data)

    def key(self):
        return datastore.Key.from_path("auth_user", self.id)


class ContextStackTests(TestCase):

    def test_push_pop(self):
        stack = ContextStack()

        self.assertEqual({}, stack.top.cache)

        entity = FakeEntity({"bananas": 1})

        stack.top.cache_entity(["bananas:1"], entity, caching.CachingSituation.DATASTORE_PUT)

        self.assertEqual({"bananas": 1}, stack.top.cache.values()[0])

        stack.push()

        self.assertEqual([], stack.top.cache.values())
        self.assertEqual(2, stack.size)

        stack.push()

        stack.top.cache_entity(["apples:2"], entity, caching.CachingSituation.DATASTORE_PUT)

        self.assertItemsEqual(["apples:2"], stack.top.cache.keys())

        stack.pop()

        self.assertItemsEqual([], stack.top.cache.keys())
        self.assertEqual(2, stack.size)
        self.assertEqual(1, stack.staged_count)

        updated = FakeEntity({"bananas": 3})

        stack.top.cache_entity(["bananas:1"], updated, caching.CachingSituation.DATASTORE_PUT)

        stack.pop(apply_staged=True, clear_staged=True)

        self.assertEqual(1, stack.size)
        self.assertEqual({"bananas": 3}, stack.top.cache["bananas:1"])
        self.assertEqual(0, stack.staged_count)

    def test_property_deletion(self):
        stack = ContextStack()

        entity = FakeEntity({"field1": "one", "field2": "two"})

        stack.top.cache_entity(["entity"], entity, caching.CachingSituation.DATASTORE_PUT)

        stack.push() # Enter transaction

        entity["field1"] = "oneone"
        del entity["field2"]

        stack.top.cache_entity(["entity"], entity, caching.CachingSituation.DATASTORE_PUT)

        stack.pop(apply_staged=True, clear_staged=True)

        self.assertEqual({"field1": "oneone"}, stack.top.cache["entity"])



class CachingTestModel(models.Model):

    field1 = models.CharField(max_length=255, unique=True)
    comb1 = models.IntegerField(default=0)
    comb2 = models.CharField(max_length=255)

    class Meta:
        unique_together = [
            ("comb1", "comb2")
        ]

        app_label = "djangae"


class MemcacheCachingTests(TestCase):
    """
        We need to be pretty selective with our caching in memcache, because unlike
        the context caching, this stuff is global.

        For that reason, we have the following rules:

         - save/update caches entities outside transactions
         - Inside transactions save/update wipes out the cache for updated entities (a subsequent read by key will populate it again)
         - Inside transactions filter/get does not hit memcache (that just breaks transactions)
         - filter/get by key caches entities (consistent)
         - filter/get by anything else does not (eventually consistent)
    """

    def setUp(self, *args, **kwargs):
        caching._local.memcache.set_sync_mode(True)
        return super(MemcacheCachingTests, self).setUp(*args, **kwargs)

    def tearDown(self, *args, **kwargs):
        caching._local.memcache.set_sync_mode(False)
        return super(MemcacheCachingTests, self).tearDown(*args, **kwargs)

    @disable_cache(memcache=False, context=True)
    def test_save_inside_transaction_evicts_cache(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        identifiers = caching._apply_namespace(
            unique_utils.unique_identifiers_from_entity(CachingTestModel, FakeEntity(entity_data, id=222)),
            DEFAULT_NAMESPACE,
        )

        instance = CachingTestModel.objects.create(id=222, **entity_data)
        instance.refresh_from_db() # Adds to memcache (consistent Get)

        for identifier in identifiers:
            self.assertEqual(entity_data, cache.get(identifier))

        with transaction.atomic():
            instance.field1 = "Banana"
            instance.save()

        # Make sure that altering inside the transaction evicted the item from the cache
        # and that a get then hits the datastore (which then in turn caches)
        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
            for identifier in identifiers:
                self.assertIsNone(cache.get(identifier))

            self.assertEqual("Banana", CachingTestModel.objects.get(pk=instance.pk).field1)
            self.assertTrue(datastore_get.called)


    @disable_cache(memcache=False, context=True)
    def test_save_caches_outside_transaction_only(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        identifiers = caching._apply_namespace(
            unique_utils.unique_identifiers_from_entity(CachingTestModel, FakeEntity(entity_data, id=222)),
            DEFAULT_NAMESPACE,
        )

        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

        instance = CachingTestModel.objects.create(id=222, **entity_data)
        instance.refresh_from_db()

        for identifier in identifiers:
            self.assertEqual(entity_data, cache.get(identifier))

        instance.delete()

        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

        with transaction.atomic():
            instance = CachingTestModel.objects.create(**entity_data)

        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

    @disable_cache(memcache=False, context=True)
    def test_save_wipes_entity_from_cache_inside_transaction(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        identifiers = caching._apply_namespace(
            unique_utils.unique_identifiers_from_entity(CachingTestModel, FakeEntity(entity_data, id=222)),
            DEFAULT_NAMESPACE,
        )

        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

        instance = CachingTestModel.objects.create(id=222, **entity_data)
        instance.refresh_from_db() # Add to memcache (consistent Get)

        for identifier in identifiers:
            self.assertEqual(entity_data, cache.get(identifier))

        with transaction.atomic():
            instance.save()

        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

    @disable_cache(memcache=False, context=True)
    def test_transactional_save_wipes_the_cache_only_after_its_result_is_consistently_available(self):
        entity_data = {
            "field1": "old",
        }

        identifiers = caching._apply_namespace(
            unique_utils.unique_identifiers_from_entity(
                CachingTestModel, FakeEntity(entity_data, id=222)
            ),
            DEFAULT_NAMESPACE,
        )

        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

        instance = CachingTestModel.objects.create(id=222, **entity_data)
        instance.refresh_from_db() # Add to memcache (consistent Get)

        for identifier in identifiers:
            self.assertEqual("old", cache.get(identifier)["field1"])

        @non_transactional
        def non_transactional_read(instance_pk):
            CachingTestModel.objects.get(pk=instance_pk)

        with transaction.atomic():
            instance.field1 = "new"
            instance.save()
            non_transactional_read(instance.pk)  # could potentially recache the old object


        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

    @disable_cache(memcache=False, context=True)
    def test_consistent_read_updates_memcache_outside_transaction(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        identifiers = caching._apply_namespace(
            unique_utils.unique_identifiers_from_entity(CachingTestModel, FakeEntity(entity_data, id=222)),
            DEFAULT_NAMESPACE,
        )

        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

        instance = CachingTestModel.objects.create(id=222, **entity_data)
        instance.refresh_from_db() # Add to memcache (consistent Get)

        for identifier in identifiers:
            self.assertEqual(entity_data, cache.get(identifier))

        cache.clear()

        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

        CachingTestModel.objects.get(id=222) # Consistent read

        for identifier in identifiers:
            self.assertEqual(entity_data, cache.get(identifier))

    @disable_cache(memcache=False, context=True)
    def test_eventual_read_doesnt_update_memcache(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        identifiers = caching._apply_namespace(
            unique_utils.unique_identifiers_from_entity(CachingTestModel, FakeEntity(entity_data, id=222)),
            DEFAULT_NAMESPACE,
        )

        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

        instance = CachingTestModel.objects.create(id=222, **entity_data)
        instance.refresh_from_db() # Add to memcache (consistent Get)

        for identifier in identifiers:
            self.assertEqual(entity_data, cache.get(identifier))

        cache.clear()

        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

        CachingTestModel.objects.all()[0] # Inconsistent read

        for identifier in identifiers:
            self.assertIsNone(cache.get(identifier))

    @disable_cache(memcache=False, context=True)
    def test_unique_filter_hits_memcache(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)
        original.refresh_from_db()

        with sleuth.watch("google.appengine.api.datastore.Query.Run") as datastore_query:
            instance = CachingTestModel.objects.filter(field1="Apple").all()[0]
            self.assertEqual(original, instance)

        self.assertFalse(datastore_query.called)

    @disable_cache(memcache=False, context=True)
    def test_unique_filter_applies_all_filters(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        CachingTestModel.objects.create(**entity_data)
        # Expect no matches
        num_instances = CachingTestModel.objects.filter(field1="Apple", comb1=0).count()
        self.assertEqual(num_instances, 0)

    @disable_cache(memcache=False, context=True)
    def test_non_unique_filter_hits_datastore(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)

        with sleuth.watch("google.appengine.api.datastore.Query.Run") as datastore_query:
            instance = CachingTestModel.objects.filter(comb1=1).all()[0]
            self.assertEqual(original, instance)

        self.assertTrue(datastore_query.called)

    @disable_cache(memcache=False, context=True)
    def test_get_by_key_hits_memcache(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)
        original.refresh_from_db() # Add to memcache (consistent Get)

        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
            instance = CachingTestModel.objects.get(pk=original.pk)
            self.assertEqual(original, instance)

        self.assertFalse(datastore_get.called)

    @disable_cache(memcache=False, context=True)
    def test_get_by_key_hits_datastore_inside_transaction(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)

        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
            with transaction.atomic():
                instance = CachingTestModel.objects.get(pk=original.pk)
            self.assertEqual(original, instance)

        self.assertTrue(datastore_get.called)

    @disable_cache(memcache=False, context=True)
    def test_unique_get_hits_memcache(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)
        original.refresh_from_db()

        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
            instance = CachingTestModel.objects.get(field1="Apple")
            self.assertEqual(original, instance)

        self.assertFalse(datastore_get.called)

    @disable_cache(memcache=False, context=True)
    def test_unique_get_hits_datastore_inside_transaction(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        CachingTestModel.objects.create(**entity_data)

        with sleuth.watch("google.appengine.api.datastore.Query.Run") as datastore_query:
            with transaction.atomic():
                try:
                    CachingTestModel.objects.get(field1="Apple")
                except datastore_errors.BadRequestError:
                    # You can't query in a transaction, but still
                    pass

        self.assertTrue(datastore_query.called)

    @disable_cache(memcache=False, context=True)
    def test_bulk_cache(self):
        with sleuth.watch("djangae.db.backends.appengine.caching.KeyPrefixedClient.set_multi_async") as set_many_1:
            instance = CachingTestModel.objects.create(field1="Apple", comb1=1, comb2="Cherry")
            instance.refresh_from_db()

        self.assertEqual(set_many_1.call_count, 1)
        self.assertEqual(len(set_many_1.calls[0].args[1]), 3)

        CachingTestModel.objects.bulk_create([
            CachingTestModel(field1="Banana", comb1=2, comb2="Cherry"),
            CachingTestModel(field1="Orange", comb1=3, comb2="Cherry"),
        ])


        pks = list(CachingTestModel.objects.values_list('pk', flat=True))
        with sleuth.watch("djangae.db.backends.appengine.caching.KeyPrefixedClient.set_multi_async") as set_many_3:
            list(CachingTestModel.objects.filter(pk__in=pks).all())
        self.assertEqual(set_many_3.call_count, 1)
        self.assertEqual(len(set_many_3.calls[0].args[1]), 3*len(pks))

        with sleuth.watch("djangae.db.backends.appengine.caching.KeyPrefixedClient.get_multi") as get_many:
            with sleuth.watch("djangae.db.backends.appengine.caching.KeyPrefixedClient.delete_multi_async") as delete_many:
                CachingTestModel.objects.all().delete()

        self.assertEqual(get_many.call_count, 1)
        self.assertEqual(delete_many.call_count, 1)
        self.assertEqual(len(get_many.calls[0].args[1]), 3)  # Get by pk from cache


class ContextCachingTests(TestCase):
    """
        We can be a bit more liberal with hitting the context cache as it's
        thread-local and request-local

        The context cache is actually a stack. When you start a transaction we push a
        copy of the current context onto the stack, when we finish a transaction we pop
        the current context and apply the changes onto the outer transaction.

        The rules are thus:

        - Entering a transaction pushes a copy of the current context
        - Rolling back a transaction pops the top of the stack
        - Committing a transaction pops the top of the stack, and adds it to a queue
        - When all transactions exit, the queue is applied to the current context one at a time
        - save/update caches entities
        - filter/get by key caches entities (consistent)
        - filter/get by anything else does not (eventually consistent)
    """

    @disable_cache(memcache=True, context=False)
    def test_that_transactions_dont_inherit_context_cache(self):
        """
            It's fine to hit the context cache inside an independent transaction,
            providing that the cache doesn't inherit the outer cache! Otherwise we have
            a situation where the transaction never hits the database when reloading an entity
        """
        entity_data = {
            "field1": u"Apple",
            "comb1": 1,
            "comb2": u"Cherry"
        }

        instance = CachingTestModel.objects.create(**entity_data)

        with transaction.atomic():
            with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
                instance = CachingTestModel.objects.get(pk=instance.pk)
                self.assertEqual(1, datastore_get.call_count) # Shouldn't hit the cache!
                instance.save()

            with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
                self.assertEqual(0, datastore_get.call_count) # Should hit the cache


    @disable_cache(memcache=True, context=False)
    def test_caching_bug(self):
        entity_data = {
            "field1": u"Apple",
            "comb1": 1,
            "comb2": u"Cherry"
        }

        instance = CachingTestModel.objects.create(**entity_data)

        expected = entity_data.copy()
        expected[u"id"] = instance.pk

        # Fetch the object, which causes it to be added to the context cache
        self.assertItemsEqual(CachingTestModel.objects.filter(pk=instance.pk).values(), [expected])
        # Doing a .values_list() fetches from the cache and wipes out the other fields from the entity
        self.assertItemsEqual(CachingTestModel.objects.filter(pk=instance.pk).values_list("field1"), [("Apple",)])
        # Now fetch from the cache again, checking that the previously wiped fields are still in tact
        self.assertItemsEqual(CachingTestModel.objects.filter(pk=instance.pk).values(), [expected])


    @disable_cache(memcache=True, context=False)
    def test_transactions_get_their_own_context(self):
        with sleuth.watch("djangae.db.backends.appengine.context.ContextStack.push") as context_push:
            with transaction.atomic():
                pass

            self.assertTrue(context_push.called)

    @disable_cache(memcache=True, context=False)
    def test_independent_transaction_applies_to_outer_context(self):
        """
            When a transaction commits successfully, we can apply its cache to the outer stack. This
            alters the behaviour of transactions a little but in a positive way. Things that change are:

            1. If you run an independent transaction inside another transaction, a subsequent Get for an entity
               updated there will return the updated instance from the cache. Due to serialization of transactions
               it's possible that this would have happened anyway (the outer transaction wouldn't start until the independent
               one had finished). It makes this behaviour consistent even when serialization isn't possible.
            2. Due to the fact the context cache is hit within a transaction, you can now Put, then Get an entity and it
               will return its current state (as the transaction would see it), rather than the state at the beginning of the
               transaction. This behaviour is nicer than the default.
        """

        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)
        with transaction.atomic():
            with transaction.atomic(independent=True):
                inner = CachingTestModel.objects.get(pk=original.pk)
                inner.field1 = "Banana"
                inner.save()

            outer = CachingTestModel.objects.get(pk=original.pk)
            self.assertEqual("Banana", outer.field1)

            outer.field1 = "Apple"
            outer.save()

        original = CachingTestModel.objects.get(pk=original.pk)
        self.assertEqual("Apple", original.field1)

    @disable_cache(memcache=True, context=False)
    def test_nested_transactions_dont_get_their_own_context(self):
        """
            The datastore doesn't support nested transactions, so when there is a nested
            atomic block which isn't marked as independent, the atomic is a no-op. Therefore
            we shouldn't push a context here, and we shouldn't pop it at the end either.
        """
        context = caching.get_context()
        self.assertEqual(1, context.stack.size)
        with transaction.atomic():
            self.assertEqual(2, context.stack.size)
            with transaction.atomic():
                self.assertEqual(2, context.stack.size)
                with transaction.atomic():
                    self.assertEqual(2, context.stack.size)
                self.assertEqual(2, context.stack.size)
            self.assertEqual(2, context.stack.size)
        self.assertEqual(1, context.stack.size)

    @disable_cache(memcache=True, context=False)
    def test_nested_rollback_doesnt_apply_on_outer_commit(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)
        with transaction.atomic():
            try:
                with transaction.atomic(independent=True):
                    inner = CachingTestModel.objects.get(pk=original.pk)
                    inner.field1 = "Banana"
                    inner.save()
                    raise ValueError() # Will rollback the transaction
            except ValueError:
                pass

            outer = CachingTestModel.objects.get(pk=original.pk)
            self.assertEqual("Apple", outer.field1)

        original = CachingTestModel.objects.get(pk=original.pk)
        self.assertEqual("Apple", original.field1) # Shouldn't have changed

    def test_save_caches(self):
        """ Test that after saving something, it exists in the context cache and therefore when we
            fetch it we don't hit memcache or the Datastore.
        """
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)

        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
            with sleuth.watch("google.appengine.api.memcache.get") as memcache_get:
                with sleuth.watch("google.appengine.api.memcache.get_multi") as memcache_get_multi:
                    original = CachingTestModel.objects.get(pk=original.pk)

        self.assertFalse(datastore_get.called)
        self.assertFalse(memcache_get.called)
        self.assertFalse(memcache_get_multi.called)

    @disable_cache(memcache=True, context=False)
    def test_consistent_read_updates_cache_outside_transaction(self):
        """
            A read inside a transaction shouldn't update the context cache outside that
            transaction
        """
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)

        caching.get_context().reset(keep_disabled_flags=True)

        CachingTestModel.objects.get(pk=original.pk) # Should update the cache

        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
            CachingTestModel.objects.get(pk=original.pk)

        self.assertFalse(datastore_get.called)

        caching.get_context().reset(keep_disabled_flags=True)

        with transaction.atomic():
            with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
                CachingTestModel.objects.get(pk=original.pk) # Should *not* update the cache
                self.assertTrue(datastore_get.called)

        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
            CachingTestModel.objects.get(pk=original.pk)

        self.assertTrue(datastore_get.called)

    @disable_cache(memcache=True, context=False)
    def test_inconsistent_read_doesnt_update_cache(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)

        caching.get_context().reset(keep_disabled_flags=True)

        CachingTestModel.objects.all() # Inconsistent

        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
            CachingTestModel.objects.get(pk=original.pk)

        self.assertTrue(datastore_get.called)

    @disable_cache(memcache=True, context=False)
    def test_unique_filter_hits_cache(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        CachingTestModel.objects.create(**entity_data)

        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
            list(CachingTestModel.objects.filter(field1="Apple"))

        self.assertFalse(datastore_get.called)

    @disable_cache(memcache=True, context=False)
    def test_unique_filter_applies_all_filters(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)

        with sleuth.watch("google.appengine.api.datastore.Query.Run") as datastore_query:
            # Expect no matches
            num_instances = CachingTestModel.objects.filter(field1="Apple", comb1=0).count()
            self.assertEqual(num_instances, 0)

    @disable_cache(memcache=True, context=False)
    def test_get_by_key_hits_cache(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        original = CachingTestModel.objects.create(**entity_data)

        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
            CachingTestModel.objects.get(pk=original.pk)

        self.assertFalse(datastore_get.called)

    @disable_cache(memcache=True, context=False)
    def test_unique_get_hits_cache(self):
        entity_data = {
            "field1": "Apple",
            "comb1": 1,
            "comb2": "Cherry"
        }

        CachingTestModel.objects.create(**entity_data)

        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
            CachingTestModel.objects.get(field1="Apple")

        self.assertFalse(datastore_get.called)

    @disable_cache(memcache=True, context=False)
    def test_context_cache_cleared_after_request(self):
        """ The context cache should be cleared between requests. """
        CachingTestModel.objects.create(field1="test")
        with sleuth.watch("google.appengine.api.datastore.Query.Run") as query:
            CachingTestModel.objects.get(field1="test")
            self.assertEqual(query.call_count, 0)
            # Now start a new request, which should clear the cache
            request_started.send(HttpRequest(), keep_disabled_flags=True)
            CachingTestModel.objects.get(field1="test")
            self.assertEqual(query.call_count, 1)
            # Now do another call, which should use the cache (because it would have been
            # populated by the previous call)
            CachingTestModel.objects.get(field1="test")
            self.assertEqual(query.call_count, 1)
            # Now clear the cache again by *finishing* a request
            request_finished.send(HttpRequest(), keep_disabled_flags=True)
            CachingTestModel.objects.get(field1="test")
            self.assertEqual(query.call_count, 2)
