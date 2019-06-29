# STANDARD LIB
import hashlib

# THIRD PARTY
from django.utils import timezone

# DJANGAE
from djangae.test import TestCase
from .lock import Lock, lock, LockAcquisitionError
from .models import DatastoreLock
from .views import cleanup_locks


class DatastoreLocksTestCase(TestCase):
    """ Tests for the implementation of the STRONG kind of lock (DatastoreLock). """

    def _make_lock(self, identifier, **kwargs):
        """ Shorcut for when we need to manually create DatastoreLock objects for tests. """
        identifier_hash = hashlib.md5(identifier).hexdigest()
        return DatastoreLock.objects.create(identifier_hash=identifier_hash, **kwargs)

    def test_acquire_and_release(self):
        # If we try to acquire the same lock twice then the second one should fail
        lock = Lock.acquire("my_lock")
        self.assertTrue(isinstance(lock, Lock))
        # Now if we try to acquire the same one again before releasing it, we should get None
        lock_again = Lock.acquire("my_lock", wait=False)
        self.assertIsNone(lock_again)
        # Now if we release it we should then be able to acquire it again
        lock.release()
        lock_again = Lock.acquire("my_lock", wait=False)
        self.assertTrue(isinstance(lock_again, Lock))

    def test_context_manager_no_wait(self):
        """ If the lock is already acquired, then our context manager with wait=False should raise
            LockAcquisitionError.
        """
        def do_context():
            with lock('x', wait=False):
                return True

        # With the lock already in use, the context manager should blow up
        my_lock = Lock.acquire('x')
        self.assertRaises(LockAcquisitionError, do_context)
        # And with the lock released the context should be run
        my_lock.release()
        self.assertTrue(do_context())

    def test_context_manager_steal(self):
        """ If the lock is already acquired, but is older than our limit then the context manager
            should steal it.
        """
        def do_context():
            with lock('x', wait=True, steal_after_ms=10):
                return True

        self._make_lock('x', timestamp=timezone.now() - timezone.timedelta(microseconds=2000))
        self.assertTrue(do_context())

    def test_decorator_no_wait(self):
        """ If the lock is already acquired, then our decorator with wait=False should not run the
            function.
        """
        @lock('x', wait=False)
        def do_something():
                return True

        # With the lock already in use, the function should not be run
        my_lock = Lock.acquire('x')
        self.assertIsNone(do_something())
        # And with the lock released the function should run
        my_lock.release()
        self.assertTrue(do_something())

    def test_decorator_steal(self):
        """ If the lock is already acquired, but is older than our limit then the decorator should
            steal it.
        """
        @lock('x', wait=True, steal_after_ms=10)
        def do_something():
                return True

        self._make_lock('x', timestamp=timezone.now() - timezone.timedelta(microseconds=2000))
        self.assertTrue(do_something())

    def test_cleanup_view(self):
        ages_ago = timezone.now() - timezone.timedelta(minutes=15)
        self._make_lock("old_lock", timestamp=ages_ago)
        recent_lock = self._make_lock("recent_lock")
        cleanup_locks(None)
        self.process_task_queues()
        # The old lock should have been deleted but the new one should not
        self.assertItemsEqual(DatastoreLock.objects.all(), [recent_lock])
