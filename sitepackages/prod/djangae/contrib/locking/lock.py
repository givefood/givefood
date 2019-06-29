# STANDARD LIB
from functools import wraps

# DJANGAE
from .kinds import LOCK_KINDS
from .memcache import MemcacheLock


class LockAcquisitionError(Exception):
    pass


class Lock(object):
    """ Common interface for acquiring and releasing a lock of the given kind.
        This is a lower-level interface than the `lock` decorator/context manager for cases where
        you need to acquire and release the lock(s) manually.
    """

    def __repr__(self):
        return u"<Lock (%s) '%s'>" % (self._kind, self._identifier)

    @classmethod
    def acquire(cls, identifier, wait=True, steal_after_ms=None, kind=LOCK_KINDS.STRONG):
        if kind == LOCK_KINDS.STRONG:
            from .models import DatastoreLock  # Avoid importing models before they're ready
            lock = DatastoreLock.objects.acquire(
                identifier, wait=wait, steal_after_ms=steal_after_ms
            )
        else:
            lock = MemcacheLock.acquire()

        if lock is None:
            return None

        instance = cls()
        instance._lock = lock
        # These two attributes are stored only for the benefit of the __repr__ method
        instance._identifier = identifier
        instance._kind = kind
        return instance

    def release(self):
        self._lock.release()


class LocknessMonster(object):
    """ Function decorator and context manager for locking a function or block of code so that only
        1 thread can excecute it at any given time.
        `identifier` should be a string which uniquely identifies the block of code that you want
        to lock.
        If `wait` is False and another thread is already running then:
            If used as a decorator, the function will not be run.
            If used as a context manager, LockAcquisitionError will be raised when entering `with`.
        If `steal_after_ms` is passed then existing locks on this function which are older
        than this value will be ignored.
    """

    def __init__(self, identifier, wait=True, steal_after_ms=None, kind=LOCK_KINDS.STRONG):
        self.identifier = identifier
        self.wait = wait
        self.steal_after_ms = steal_after_ms
        self.kind = kind

    def __call__(self, function):
        @wraps(function)
        def replacement_function(*args, **kwargs):
            try:
                with self:
                    return function(*args, **kwargs)
            except LockAcquisitionError:
                # In the case where self.wait is False and the Lock is already in use self.__enter__
                # will raise this exception
                return  # Do not run the function
        return replacement_function

    def __enter__(self):
        self.lock = Lock.acquire(self.identifier, self.wait, self.steal_after_ms, self.kind)
        if self.lock is None:
            raise LockAcquisitionError("Failed to acquire lock for '%s'" % self.identifier)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.lock:
            self.lock.release()
            self.lock = None  # Just for neatness


lock = LocknessMonster
