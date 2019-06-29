from django.apps import AppConfig
from django.contrib import auth
from django.contrib.auth.management import create_permissions
from django.db.models.signals import post_migrate




# This is slightly unnecessary, because if the project is importing this file then it is *probably*
# using one of the user models defined in here.  But for the sake of not getting things in a twist
# when switching user models in tests, etc, we still use this conditional bypassing of the call to
# Django's create_permissions() function

def lazy_permission_creation(**kwargs):
    from .models import PermissionsMixin
    if issubclass(auth.get_user_model(), PermissionsMixin):
        return

    # Call through to Django's create_permissions
    create_permissions(**kwargs)


class GAuthDatastoreConfig(AppConfig):

   name = "djangae.contrib.gauth.datastore"
   verbose_name = "gauth"

   def ready(self):

        post_migrate.disconnect(
            dispatch_uid="django.contrib.auth.management.create_permissions")
        post_migrate.connect(
            lazy_permission_creation,
            sender=self,
            dispatch_uid="django.contrib.auth.management.create_permissions",
        )
