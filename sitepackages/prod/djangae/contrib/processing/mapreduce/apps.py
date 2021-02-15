from __future__ import absolute_import

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _


class MapreduceConfig(AppConfig):
    name = 'mapreduce'
    verbose_name = _("Mapreduce")

    def ready(self):
        try:
            import mapreduce

            # This is awful, but necessary unless we want to get people to start fiddling
            # with appengine_config.py :/
            mapreduce.parameters.config.BASE_PATH = '/_ah/mapreduce'
            mapreduce.parameters._DEFAULT_PIPELINE_BASE_PATH = "/_ah/mapreduce/pipeline"
        except ImportError:
            raise ImproperlyConfigured(
                "To use djangae.contrib.processing.mapreduce you must have the "
                "AppEngineMapreduce library installed."
            )
