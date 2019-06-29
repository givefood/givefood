from django.contrib.auth.models import PermissionsMixin
from django.utils.translation import ugettext_lazy as _

from djangae.contrib.gauth.common.models import GaeAbstractBaseUser


class GaeAbstractUser(GaeAbstractBaseUser, PermissionsMixin):
    """
    Abstract user class for SQL databases.
    """
    class Meta:
        abstract = True


class GaeUser(GaeAbstractBaseUser, PermissionsMixin):
    """ A basic user model which can be used with GAE authentication.
        Essentially the equivalent of django.contrib.auth.models.User.
        Cannot be used with permissions when using the Datastore, because it
        uses the standard django permissions models which use M2M relationships.
    """

    class Meta:
        app_label = "djangae"
        swappable = 'AUTH_USER_MODEL'
        verbose_name = _('user')
        verbose_name_plural = _('users')
