# This is essentially a slimmed down mapreduce. There are some differences with the sharding logic
# and the whole thing leverages defer and there's no reducing, just mapping.

# If you're wondering why we're not using MR here...
# 1. We don't want a hard dependency on it and migrations are core (unlike stuff in contrib)
# 2. MR is massive overkill for what we're doing here

import copy
import cPickle
import itertools
import logging
from datetime import datetime

from django.conf import settings
from django.utils.six.moves import range
from google.appengine.api import datastore_errors
from google.appengine.api.taskqueue.taskqueue import _DEFAULT_QUEUE
from google.appengine.ext import deferred
from google.appengine.runtime import DeadlineExceededError

from djangae.db.backends.appengine import rpc


logger = logging.getLogger(__name__)


class Redefer(Exception):
    """ Custom exception class to allow triggering of the re-deferring of a processing task. """
    pass


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    # Copied from Python docs.
    a, b = itertools.tee(iterable)
    next(b, None)

    return itertools.izip(a, b)


def good_fit_step(x, y):
    """Returns a step interval to use when selecting keys.

    The step will ensure that we create no more than num_shards.
    """
    step, remainder = divmod(x, y)

    if remainder:
        step = (x + remainder) // y

    if step == 0:
        step = 1

    return step


def generate_shards(keys, shard_count):
    """Returns a list of key pairs, where the last pair is like (<key>, None).

    Each (start, stop) pair can be used to filter entities like:

      WHERE __key__ >= start AND __key__ < stop

    (Except for the last pair, when stop is None). Note this will never return
    more than shard_count pairs.

    >>> keys = [1, 2, 3, 4, 5]
    >>> generate_shards(keys, shard_count=1)
    [(1, None)]
    >>> generate_shards(keys, shard_count=2)
    [(1, 4), (4, None)]
    >>> generate_shards(keys, shard_count=5)
    [(1, 2), (2, 3), (3, 4), (4, 5), (5, None)]
    """
    step = good_fit_step(len(keys), shard_count)

    keys = sorted(keys)  # Ensure the keys are sorted
    keys = keys[::step]

    # The last key pair looks like (<key>, None). See where we build the entity
    # query in ShardedTaskManager.run_shard().
    keys.append(None)

    shards = list(pairwise(keys))

    return shards


def shard_query(query, shard_count):
    """ Given a rpc.Query object and a number of shards, return a list of shards where each
        shard is a pair of (low_key, high_key).
        May return fewer than `shard_count` shards in cases where there aren't many entities.
    """
    OVERSAMPLING_MULTIPLIER = 32  # This value is used in Mapreduce

    try:
        query.Order("__key__")
        min_id = query.Run().next().key()

        query.Order(("__key__", query.DESCENDING))
        max_id = query.Run().next().key()
    except StopIteration:
        # No objects, so no shards
        return []

    query.Order("__scatter__")  # Order by the scatter property

    # Get random keys to shard on
    keys = [x.key() for x in query.Get(shard_count * OVERSAMPLING_MULTIPLIER)]
    keys.sort()

    if not keys:  # If no keys...
        # Shard on the upper and lower PKs in the query this is *not* efficient
        keys = [min_id, max_id]
    else:
        if keys[0] != min_id:
            keys.insert(0, min_id)

        if keys[-1] != max_id:
            keys.append(max_id)

    shards = generate_shards(keys, shard_count)

    return shards


class ShardedTaskMarker(rpc.Entity):
    """ Manages the running of an operation over the entities of a query using multiple processing
        tasks.  Stores details of the current state on itself as an Entity in the rpc.
    """
    KIND = "_djangae_migration_task"

    QUEUED_KEY = "shards_queued"
    RUNNING_KEY = "shards_running"
    FINISHED_KEY = "shards_finished"

    def __init__(self, identifier, query, *args, **kwargs):
        kwargs["kind"] = self.KIND
        kwargs["name"] = identifier

        super(ShardedTaskMarker, self).__init__(*args, **kwargs)

        self[ShardedTaskMarker.QUEUED_KEY] = []
        self[ShardedTaskMarker.RUNNING_KEY] = []
        self[ShardedTaskMarker.FINISHED_KEY] = []
        self["time_started"] = None
        self["time_finished"] = None
        self["query"] = cPickle.dumps(query)
        self["is_finished"] = False

    @classmethod
    def get_key(cls, identifier, namespace):
        return rpc.Key.from_path(
            cls.KIND,
            identifier,
            namespace=namespace
        )

    def put(self, *args, **kwargs):
        if not self["is_finished"]:
            # If we aren't finished, see if we are now
            # This if-statement is important because if a task had no shards
            # it would be 'finished' immediately so we don't want to incorrectly
            # set it to False when we save if we manually set it to True
            self["is_finished"] = bool(
                not self[ShardedTaskMarker.QUEUED_KEY] and
                not self[ShardedTaskMarker.RUNNING_KEY] and
                self[ShardedTaskMarker.FINISHED_KEY]
            )

            if self["is_finished"]:
                self["time_finished"] = datetime.utcnow()

        rpc.Put(self)

    def run_shard(
        self, original_query, shard, operation, operation_method=None, offset=0,
        entities_per_task=None, queue=_DEFAULT_QUEUE
    ):
        """ Given a rpc.Query which does not have any high/low bounds on it, apply the bounds
            of the given shard (which is a pair of keys), and run either the given `operation`
            (if it's a function) or the given method of the given operation (if it's an object) on
            each entity that the query returns, starting at entity `offset`, and redeferring every
            `entities_per_task` entities to avoid hitting DeadlineExceededError.
            Tries (but does not guarantee) to avoid processing the same entity more than once.
        """
        entities_per_task = entities_per_task or getattr(
            settings, "DJANGAE_MIGRATION_DEFAULT_ENTITIES_PER_TASK", 100
        )
        if operation_method:
            function = getattr(operation, operation_method)
        else:
            function = operation

        marker = rpc.Get(self.key())
        if cPickle.dumps(shard) not in marker[ShardedTaskMarker.RUNNING_KEY]:
            return

        # Copy the query so that we can re-defer the original, unadulterated version, because once
        # we've applied limits and ordering to the query it causes pickle errors with defer.
        start_key, stop_key = shard
        query = copy.deepcopy(original_query)
        query.Order("__key__")
        query["__key__ >="] = start_key

        # The last key pair looks like (<key>, None). When querying entities,
        # the first key is inclusive and the second key is exclusive. But if
        # the stop key is None then this must be the last shard so we omit the
        # upper limit clause.
        if stop_key is not None:
            query["__key__ <"] = stop_key

        num_entities_processed = 0
        try:
            results = query.Run(offset=offset, limit=entities_per_task)
            for entity in results:
                function(entity)
                num_entities_processed += 1
                if num_entities_processed >= entities_per_task:
                    raise Redefer()
        except (DeadlineExceededError, Redefer):
            # By keeping track of how many entities we've processed, we can (hopefully) avoid
            # re-processing entities if we hit DeadlineExceededError by redeferring with the
            # incremented offset.  But note that if we get crushed by the HARD DeadlineExceededError
            # before we can redefer, then the whole task will retry and so entities will get
            # processed twice.
            deferred.defer(
                self.run_shard,
                original_query,
                shard,
                operation,
                operation_method,
                offset=offset + num_entities_processed,
                entities_per_task=entities_per_task,
                # Defer this task onto the correct queue (with `_queue`), passing the `queue`
                # parameter back to the function again so that it can do the same next time
                queue=queue,
                _queue=queue,
            )
            return  # This is important!

        # Once we've run the operation on all the entities, mark the shard as done
        def txn():
            pickled_shard = cPickle.dumps(shard)
            marker = rpc.Get(self.key())
            marker.__class__ = ShardedTaskMarker
            marker[ShardedTaskMarker.RUNNING_KEY].remove(pickled_shard)
            marker[ShardedTaskMarker.FINISHED_KEY].append(pickled_shard)
            marker.put()

        rpc.RunInTransaction(txn)

    def begin_processing(self, operation, operation_method, entities_per_task, queue):
        BATCH_SIZE = 3

        # Unpickle the source query
        query = cPickle.loads(str(self["query"]))

        def txn():
            try:
                marker = rpc.Get(self.key())
                marker.__class__ = ShardedTaskMarker

                queued_shards = marker[ShardedTaskMarker.QUEUED_KEY]
                processing_shards = marker[ShardedTaskMarker.RUNNING_KEY]
                queued_count = len(queued_shards)

                for j in range(min(BATCH_SIZE, queued_count)):
                    pickled_shard = queued_shards.pop()
                    processing_shards.append(pickled_shard)
                    shard = cPickle.loads(str(pickled_shard))
                    deferred.defer(
                        self.run_shard,
                        query,
                        shard,
                        operation,
                        operation_method,
                        entities_per_task=entities_per_task,
                        # Defer this task onto the correct queue with `_queue`, passing the `queue`
                        # parameter back to the function again so that it can do the same next time
                        queue=queue,
                        _queue=queue,
                        _transactional=True,
                    )

                marker.put()
            except datastore_errors.EntityNotFoundError:
                logger.error(
                    "Unable to start task %s as marker is missing",
                    self.key().id_or_name()
                )
                return

        # Reload the marker (non-transactionally) and defer the shards in batches
        # transactionally. If this task fails somewhere, it will resume where it left off
        marker = rpc.Get(self.key())
        for i in range(0, len(marker[ShardedTaskMarker.QUEUED_KEY]), BATCH_SIZE):
            rpc.RunInTransaction(txn)


def start_mapping(
    identifier, query, operation, operation_method=None, shard_count=None,
    entities_per_task=None, queue=None
):
    """ This must *transactionally* defer a task which will call `operation._wrapped_map_entity` on
        all entities of the given `kind` in the given `namespace` and will then transactionally
        update the entity of the given `task_marker_key_key` with `is_finished=True` after all
        entities have been mapped.
    """
    shard_count = shard_count or getattr(settings, "DJANGAE_MIGRATION_DEFAULT_SHARD_COUNT", 32)
    shards_to_run = shard_query(query, shard_count)
    queue = queue or getattr(settings, "DJANGAE_MIGRATION_DEFAULT_QUEUE", _DEFAULT_QUEUE)

    def txn(shards):
        marker_key = ShardedTaskMarker.get_key(identifier, query._Query__namespace)
        try:
            rpc.Get(marker_key)

            # If the marker already exists, don't do anything - just return
            return
        except datastore_errors.EntityNotFoundError:
            pass

        marker = ShardedTaskMarker(identifier, query, namespace=query._Query__namespace)

        if shards:
            for shard in shards:
                marker["shards_queued"].append(cPickle.dumps(shard))
        else:
            # No shards, then there is nothing to do!
            marker["is_finished"] = True
        marker["time_started"] = datetime.utcnow()
        marker.put()
        if not marker["is_finished"]:
            deferred.defer(
                marker.begin_processing, operation, operation_method, entities_per_task, queue,
                _transactional=True, _queue=queue
            )

        return marker_key

    return rpc.RunInTransaction(txn, shards_to_run)


def mapper_exists(identifier, namespace):
    """
        Returns True if the mapper exists, False otherwise
    """
    try:
        rpc.Get(ShardedTaskMarker.get_key(identifier, namespace))
        return True
    except datastore_errors.EntityNotFoundError:
        return False


def is_mapper_finished(identifier, namespace):
    """
        Returns True if the mapper exists, and it's not running.
    """
    return mapper_exists(identifier, namespace) and not is_mapper_running(identifier, namespace)


def is_mapper_running(identifier, namespace):
    """
        Returns True if the mapper exists, but it's not finished
    """
    try:
        marker = rpc.Get(ShardedTaskMarker.get_key(identifier, namespace))
        return not marker["is_finished"]
    except datastore_errors.EntityNotFoundError:
        return False
