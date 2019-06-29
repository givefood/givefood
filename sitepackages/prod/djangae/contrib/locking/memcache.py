from .kinds import LOCK_KINDS


class MemcacheLock(object):

    @classmethod
    def acquire(cls, identifier, wait=True, steal_after_ms=None, kind=LOCK_KINDS.STRONG):
        raise NotImplementedError()

    def release(self):
        raise NotImplementedError()
