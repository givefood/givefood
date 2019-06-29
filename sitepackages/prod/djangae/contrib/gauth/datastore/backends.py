# STANDARD LIB
from itertools import chain

# DJANGAE
from djangae.db import transaction
from djangae.contrib.gauth.common.backends import BaseAppEngineUserAPIBackend
from djangae.contrib.gauth.datastore.permissions import get_permission_choices


class AppEngineUserAPIBackend(BaseAppEngineUserAPIBackend):
    atomic = transaction.atomic
    atomic_kwargs = {'xg': True}

    def get_group_permissions(self, user_obj, obj=None):
        """
        Returns a set of permission strings that this user has through his/her
        groups.
        """
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_group_perm_cache'):
            if user_obj.is_superuser:
                perms = (perm for perm, name in get_permission_choices())
            else:
                perms = chain.from_iterable((group.permissions for group in user_obj.groups.all()))
            user_obj._group_perm_cache = set(perms)
        return user_obj._group_perm_cache

    def get_all_permissions(self, user_obj, obj=None):
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_perm_cache'):
            user_obj._perm_cache = set(user_obj.user_permissions)
            user_obj._perm_cache.update(self.get_group_permissions(user_obj))
        return user_obj._perm_cache
