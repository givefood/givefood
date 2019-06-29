from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.management import update_contenttypes as django_update_contenttypes
from django.db.models.signals import post_migrate

from .management import update_contenttypes
from .models import SimulatedContentTypeManager


class ContentTypesConfig(AppConfig):
    name = 'djangae.contrib.contenttypes'
    verbose_name = _("Djangae Content Types")
    label = "djangae_contenttypes"

    def ready(self):
        if django_update_contenttypes != update_contenttypes:
            post_migrate.disconnect(django_update_contenttypes)
            from django.contrib.contenttypes import models as django_models
            if not isinstance(django_models.ContentType.objects, SimulatedContentTypeManager):
                django_models.ContentType.objects = SimulatedContentTypeManager()
