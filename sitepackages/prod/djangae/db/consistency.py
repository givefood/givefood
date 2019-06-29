import warnings
from collections import deque

from django.db.models.query import QuerySet


def _clone_queryset(qs, klass):
    cloned_qs = klass(
        model=qs.model,
        query=qs.query.clone(),
        using=qs._db,
        hints=qs._hints,
    )
    cloned_qs._for_write = qs._for_write
    cloned_qs._prefetch_related_lookups = qs._prefetch_related_lookups[:]
    cloned_qs._known_related_objects = qs._known_related_objects

    return cloned_qs


def ensure_instances_consistent(queryset, instance_pks):
    """
        HRD fighting generate for iterating querysets.
        In the common case of having just created an item, this
        inserts the item at the correct place in a subsequent query.

        This guarantees that the object will be inserted
        in the right place as per the queryset ordering. Only takes into account
        the query.order_by and not default ordering. Patches welcome!

        If the instance specified by the consistently_got_id was deleted, and it comes back
        in the subsequent query, it is removed from the resultset. This might cause an
        off-by-one number of results if you are slicing the queryset.
    """

    class EnsuredQuerySet(queryset.__class__):
        def _fetch_all(self):
            super(EnsuredQuerySet, self)._fetch_all()

            new_qs = _clone_queryset(qs=self, klass=queryset.__class__)
            new_qs.query.high_mark = None
            new_qs.query.low_mark = 0
            consistently_got = list(new_qs.filter(pk__in=instance_pks))

            def is_less(lhs, rhs):
                for field in queryset.query.order_by:
                    # Go through the fields specified in the order by
                    negative = field.startswith("-")
                    if negative:
                        field = field[1:]
                        # If the ordering was negated, but the lhs < rhs then return false
                        if getattr(lhs, field, None) < getattr(rhs, field, None):
                            return False
                    else:
                        # If the ordering was not negated, and the lhs >= rhs, return false
                        if getattr(lhs, field, None) >= getattr(rhs, field, None):
                            return False
                else:
                    return True

            new_result_cache = []
            count = self.query.high_mark

            # We sort by the is_less function and use a deque so we can pop from the
            # front
            consistently_got = deque(sorted(consistently_got, cmp=is_less))

            # Go through each item in the result set and peek at the first item in the
            # deque. If the item is the same, or the item in the deque should appear before
            # 'item' then add the consistent item. If the consistent item is == item then
            # continue so we don't add a duplicate
            for item in self._result_cache:
                try:
                    consistent_item = consistently_got[0]

                    # Should the consistent item be added?
                    if item == consistent_item or is_less(consistent_item, item):
                        new_result_cache.append(consistent_item)
                        consistently_got.popleft()
                        if item == consistent_item:
                            # Prevent adding a stale duplicate
                            continue
                except IndexError:
                    # No consistent items left, so just append all the things
                    # remaining in the original result set
                    pass

                # Item was deleted, otherwise we would have seen it in consistent_item
                if item.pk in instance_pks:
                    continue

                new_result_cache.append(item)
            else:
                # Finally, if we've been through the entire result set, and we still
                # have consistent things remaining, they must be new and at the end of the
                # ordering so just add them to the end of the result set
                if consistently_got:
                    new_result_cache.extend(list(consistently_got))

            self._result_cache = new_result_cache[:count]

    if isinstance(queryset, QuerySet):
        return _clone_queryset(qs=queryset, klass=EnsuredQuerySet)
    else:
        return queryset

def ensure_instance_consistent(queryset, instance_id):
    return ensure_instances_consistent(queryset, [ instance_id ])

def ensure_instance_included(queryset, instance_id):
    warnings.warn("ensure_instance_included is deprecated, use ensure_instance_consistent instead", DeprecationWarning)
    return ensure_instance_consistent(queryset, instance_id)
