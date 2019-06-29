from google.appengine.ext.deferred import defer
from google.appengine.runtime import DeadlineExceededError


def _process_shard(model, instance_ids, callback):
    for instance in model.objects.filter(pk__in=instance_ids):
        callback(instance)


def _shard(model, query, callback, shard_size, queue, offset=0):
    keys_queryset = model.objects.all()
    keys_queryset.query = query
    keys_queryset = keys_queryset.values_list("pk", flat=True)

    # Keep iterating until we are done, or we only have 10 seconds to spare!
    while True:
        try:
            ids = list(keys_queryset.all()[offset:offset+shard_size])
            if not ids:
                # We're done!
                return

            # Fire off the first shard
            defer(_process_shard, model, ids, callback, _queue=queue)

            # Increment the offset
            offset += shard_size
        except DeadlineExceededError:
            # If we run out of time, then defer this function again, continuing from the offset
            defer(
                _shard,
                model,
                query,
                callback,
                shard_size,
                queue,
                offset=offset,
                _queue=queue
            )


def defer_iteration(queryset, callback, shard_size=500, _queue="default", _target=None):
    """
        Shards background tasks to call 'callback' with each instance in queryset

        - `queryset` - The queryset to iterate
        - `callback` - A callable which accepts an instance as a parameter
        - `shard_size` - The number instances to process per shard (default 500)
        - `_queue` - The name of the queue to run the shards on

        Note, your callback must be indempotent, shards may retry and your callback
        may be called multiple times on the same instance. If you notice that your
        tasks are receiving DeadlineExceededErrors you probably need to reduce the
        shard size. The shards will work in parallel and will not be sequential.
    """

    # We immediately defer the _shard function so that we don't hold up execution
    defer(_shard, queryset.model, queryset.query, callback, shard_size, _queue, _queue=_queue, _target=_target)
