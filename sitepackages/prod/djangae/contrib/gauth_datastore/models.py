from django.contrib import auth
from django.contrib.auth.models import (
    python_2_unicode_compatible,
    GroupManager,
    _user_get_all_permissions,
    _user_has_perm,
    _user_has_module_perms
)
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import lazy

from djangae.fields import ListField, RelatedSetField
from djangae.contrib.gauth.models import GaeAbstractBaseUser
from djangae.contrib.gauth_datastore.permissions import get_permission_choices


@python_2_unicode_compatible
class Group(models.Model):
    """
        This is a clone of django.contrib.auth.Group, but nonrelationalized. Doesn't user Permission but directly
        uses the permission names
    """
    name = models.CharField(_('name'), max_length=80, unique=True)
    permissions = ListField(models.CharField(max_length=500),
        verbose_name=_('permissions'), blank=True
    )

    objects = GroupManager()

    class Meta:
        db_table = 'djangae_group'
        verbose_name = _('group')
        verbose_name_plural = _('groups')

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    def __init__(self, *args, **kwargs):
        """We need to override this to make the choices lazy and prevent import madness"""
        super(Group, self).__init__(*args, **kwargs)

        field = self._meta.get_field('permissions')
        field._choices = lazy(get_permission_choices, list)()
        field.item_field_type._choices = lazy(get_permission_choices, list)()


class PermissionsMixin(models.Model):
    """
    A mixin class that adds the fields and methods necessary to support
    Django's Group and Permission model using the ModelBackend.
    """
    is_superuser = models.BooleanField(_('superuser status'), default=False,
        help_text=_('Designates that this user has all permissions without '
                    'explicitly assigning them.')
    )

    groups = RelatedSetField(
        Group,
        verbose_name=_('groups'),
        blank=True, help_text=_('The groups this user belongs to. A user will '
                                'get all permissions granted to each of '
                                'his/her group.')
    )

    user_permissions = ListField(
        models.CharField(max_length=500),
        verbose_name=_('user permissions'), blank=True,
        help_text='Specific permissions for this user.'
    )

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        """We need to override this to make the choices lazy and prevent import madness"""
        super(PermissionsMixin, self).__init__(*args, **kwargs)
        self._meta.get_field('user_permissions')._choices = lazy(get_permission_choices, list)()

    def get_group_permissions(self, obj=None):
        """
        Returns a list of permission strings that this user has through his/her
        groups. This method queries all available auth backends. If an object
        is passed in, only permissions matching this object are returned.
        """
        permissions = set()
        for backend in auth.get_backends():
            if hasattr(backend, "get_group_permissions"):
                if obj is not None:
                    permissions.update(backend.get_group_permissions(self,
                                                                     obj))
                else:
                    permissions.update(backend.get_group_permissions(self))
        return permissions

    def get_all_permissions(self, obj=None):
        return _user_get_all_permissions(self, obj)

    def has_perm(self, perm, obj=None):
        """
        Returns True if the user has the specified permission. This method
        queries all available auth backends, but returns immediately if any
        backend returns True. Thus, a user who has permission from a single
        auth backend is assumed to have permission in general. If an object is
        provided, permissions for this specific object are checked.
        """

        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):
        """
        Returns True if the user has each of the specified permissions. If
        object is passed, it checks if the user has all required perms for this
        object.
        """
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

    def has_module_perms(self, app_label):
        """
        Returns True if the user has any permissions in the given app label.
        Uses pretty much the same logic as has_perm, above.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)


class GaeAbstractDatastoreUser(GaeAbstractBaseUser, PermissionsMixin):
    """ Base class for a user model which can be used with GAE authentication
        and permissions on the Datastore.
    """

    class Meta:
        abstract = True


class GaeDatastoreUser(GaeAbstractBaseUser, PermissionsMixin):
    """ A basic user model which can be used with GAE authentication and allows
        permissions to work on the Datastore backend.
    """

    class Meta:
        db_table = 'djangae_gaedatastoreuser'
        swappable = 'AUTH_USER_MODEL'
        verbose_name = _('user')
        verbose_name_plural = _('users')

