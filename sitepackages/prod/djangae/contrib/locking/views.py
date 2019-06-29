# STANDARD LIB
import logging

# THIRD PARTY
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

# DJANGAE
from djangae.contrib.mappers import defer_iteration
from .models import DatastoreLock

# GAE background tasks and crons can run for a maximum of 10 minutes, so in theory you shouldn't
# be locking a block of code which takes longer than that, and even if you're using backends which
# can run for longer, you would still be mad to lock a block of code which runs for > 10 minutes
DELETE_LOCKS_OLDER_THAN_SECONDS = 600
QUEUE = getattr(settings, 'DJANGAE_CLEANUP_LOCKS_QUEUE', 'default')


def cleanup_locks(request):
    """ Delete all Lock objects that are older than 10 minutes. """
    logging.info("Starting djangae.contrib.lock cleanup task")
    cut_off = timezone.now() - timezone.timedelta(seconds=DELETE_LOCKS_OLDER_THAN_SECONDS)
    queryset = DatastoreLock.objects.filter(timestamp__lt=cut_off)
    defer_iteration(queryset, _delete_lock, _queue=QUEUE)
    return HttpResponse("Cleanup locks task is running")


def _delete_lock(lock):
    logging.info("Deleting stale lock '%s' with timestamp %r", lock.identifier, lock.timestamp)
    lock.delete()
