# STANDARD LIB
import threading

# DJANGAE
from djangae.db import transaction
from djangae.contrib import sleuth
from djangae.test import TestCase


class TransactionTests(TestCase):
    def test_repeated_usage_in_a_loop(self):
        from .test_connector import TestUser
        pk = TestUser.objects.create(username="foo").pk
        for i in xrange(4):
            with transaction.atomic(xg=True):
                TestUser.objects.get(pk=pk)
                continue

        with transaction.atomic(xg=True):
            TestUser.objects.get(pk=pk)

    def test_recursive_atomic(self):
        l = []

        @transaction.atomic
        def txn():
            l.append(True)
            if len(l) == 3:
                return
            else:
                txn()

        txn()

    def test_recursive_non_atomic(self):
        l = []

        @transaction.non_atomic
        def txn():
            l.append(True)
            if len(l) == 3:
                return
            else:
                txn()

        txn()

    def test_atomic_in_separate_thread(self):
        """ Regression test.  See #668. """
        @transaction.atomic
        def txn():
            return

        def target():
            txn()

        thread = threading.Thread(target=target)
        thread.start()
        thread.join()

    def test_non_atomic_in_separate_thread(self):
        """ Regression test.  See #668. """
        @transaction.non_atomic
        def txn():
            return

        def target():
            txn()

        thread = threading.Thread(target=target)
        thread.start()
        thread.join()

    def test_atomic_decorator(self):
        from .test_connector import TestUser

        @transaction.atomic
        def txn():
            TestUser.objects.create(username="foo", field2="bar")
            self.assertTrue(transaction.in_atomic_block())
            raise ValueError()

        with self.assertRaises(ValueError):
            txn()

        self.assertEqual(0, TestUser.objects.count())

    def test_interaction_with_datastore_txn(self):
        from google.appengine.ext import db
        from google.appengine.datastore.datastore_rpc import TransactionOptions
        from .test_connector import TestUser

        @db.transactional(propagation=TransactionOptions.INDEPENDENT)
        def some_indie_txn(_username):
            TestUser.objects.create(username=_username)

        @db.transactional()
        def some_non_indie_txn(_username):
            TestUser.objects.create(username=_username)

        @db.transactional()
        def double_nested_transactional():
            @db.transactional(propagation=TransactionOptions.INDEPENDENT)
            def do_stuff():
                TestUser.objects.create(username="Double")
                raise ValueError()

            try:
                return do_stuff
            except:
                return

        with transaction.atomic():
            double_nested_transactional()

        @db.transactional()
        def something_containing_atomic():
            with transaction.atomic():
                TestUser.objects.create(username="Inner")

        something_containing_atomic()

        with transaction.atomic():
            with transaction.atomic():
                some_non_indie_txn("Bob1")
                some_indie_txn("Bob2")
                some_indie_txn("Bob3")

        with transaction.atomic(independent=True):
            some_non_indie_txn("Fred1")
            some_indie_txn("Fred2")
            some_indie_txn("Fred3")

    def test_atomic_context_manager(self):
        from .test_connector import TestUser

        with self.assertRaises(ValueError):
            with transaction.atomic():
                TestUser.objects.create(username="foo", field2="bar")
                raise ValueError()

        self.assertEqual(0, TestUser.objects.count())

    def test_non_atomic_context_manager(self):
        from .test_connector import TestUser
        existing = TestUser.objects.create(username="existing", field2="exists")

        with transaction.atomic():
            self.assertTrue(transaction.in_atomic_block())

            user = TestUser.objects.create(username="foo", field2="bar")

            with transaction.non_atomic():
                # We're outside the transaction, so the user should not exist
                self.assertRaises(TestUser.DoesNotExist, TestUser.objects.get, pk=user.pk)
                self.assertFalse(transaction.in_atomic_block())

                with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
                    TestUser.objects.get(pk=existing.pk)  # Should hit the cache, not the datastore

                self.assertFalse(datastore_get.called)

            with transaction.atomic(independent=True):
                user2 = TestUser.objects.create(username="foo2", field2="bar2")
                self.assertTrue(transaction.in_atomic_block())

                with transaction.non_atomic():
                    self.assertFalse(transaction.in_atomic_block())
                    self.assertRaises(TestUser.DoesNotExist, TestUser.objects.get, pk=user2.pk)

                    with transaction.non_atomic():
                        self.assertFalse(transaction.in_atomic_block())
                        self.assertRaises(TestUser.DoesNotExist, TestUser.objects.get, pk=user2.pk)

                        with sleuth.watch("google.appengine.api.datastore.Get") as datastore_get:
                            # Should hit the cache, not the Datastore
                            TestUser.objects.get(pk=existing.pk)

                    self.assertFalse(transaction.in_atomic_block())
                    self.assertRaises(TestUser.DoesNotExist, TestUser.objects.get, pk=user2.pk)

                self.assertTrue(TestUser.objects.filter(pk=user2.pk).exists())
                self.assertTrue(transaction.in_atomic_block())

    def test_xg_argument(self):
        from .test_connector import TestUser, TestFruit

        @transaction.atomic(xg=True)
        def txn(_username):
            TestUser.objects.create(username=_username, field2="bar")
            TestFruit.objects.create(name="Apple", color="pink")
            raise ValueError()

        with self.assertRaises(ValueError):
            txn("foo")

        self.assertEqual(0, TestUser.objects.count())
        self.assertEqual(0, TestFruit.objects.count())

    def test_independent_argument(self):
        """
            We would get a XG error if the inner transaction was not independent
        """
        from .test_connector import TestUser, TestFruit

        @transaction.atomic
        def txn1(_username, _fruit):
            @transaction.atomic(independent=True)
            def txn2(_fruit):
                TestFruit.objects.create(name=_fruit, color="pink")
                raise ValueError()

            TestUser.objects.create(username=_username)
            txn2(_fruit)

        with self.assertRaises(ValueError):
            txn1("test", "banana")

    def test_nested_decorator(self):
        # Nested decorator pattern we discovered can cause a connection_stack
        # underflow.

        @transaction.atomic
        def inner_txn():
            pass

        @transaction.atomic
        def outer_txn():
            inner_txn()

        # Calling inner_txn first puts it in a state which means it doesn't
        # then behave properly in a nested transaction.
        inner_txn()
        outer_txn()
