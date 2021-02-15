

def _find_random_keys(queryset, shard_count):
    OVERSAMPLING_FACTOR = 32

    return list(
        queryset.model.objects.order_by("__scatter__").values_list("pk", flat=True)[
            :(shard_count * OVERSAMPLING_FACTOR)
        ]
    )


def find_key_ranges_for_queryset(queryset, shard_count):
    """
        Given a queryset and a number of shard. This function makes use
        of the __scatter__ property to return a list of key ranges
        for sharded iteration.
    """

    if shard_count > 1:
        # Use the scatter property to generate shard points
        random_keys = _find_random_keys(queryset, shard_count)

        if not random_keys:
            # No random keys? Don't shard
            key_ranges = [(None, None)]
        else:
            random_keys.sort()

            # We have enough random keys to shard things
            if len(random_keys) >= shard_count:
                index_stride = len(random_keys) / float(shard_count)
                split_keys = [random_keys[int(round(index_stride * i))] for i in range(1, shard_count)]
            else:
                split_keys = random_keys

            key_ranges = [(None, split_keys[0])] + [
                (split_keys[i], split_keys[i + 1]) for i in range(len(split_keys) - 1)
            ] + [(split_keys[-1], None)]
    else:
        # Don't shard
        key_ranges = [(None, None)]

    return key_ranges
