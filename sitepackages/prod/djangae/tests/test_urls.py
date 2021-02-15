import importlib
import sys

from djangae.contrib import sleuth
from django.test import SimpleTestCase


class ImportingUrlsTestCase(SimpleTestCase):

    @sleuth.emplace('sys.modules', {})
    def test_importing_djangae_urls_should_not_import_mapreduce(self):
        # If you include 'djangae.urls', that should NOT trigger an import of
        # the mapreduce and pipeline when 'djangae.contrib.processing.mapreduce'
        # is not in INSTALLED_APPS.
        #
        # https://github.com/potatolondon/djangae/issues/926

        # There are lots of individual modules that are imported as part of the
        # mapreduce and pipeline packages, but we'll use the main ones for this.

        module_names = [
            'pipeline',
            'mapreduce',
        ]
        for name in module_names:
            if name in sys.modules:
                del sys.modules[name]

        djangae_urls_name = 'djangae.urls'

        if djangae_urls_name in sys.modules:
            del sys.modules[djangae_urls_name]

        # OK. The main mapreduce modules should not be present now.
        for name in module_names:
            self.assertNotIn(name, sys.modules)

        self.assertNotIn(djangae_urls_name, sys.modules)

        # Now see if this imports mapreduce libs as a side-effect.
        with self.settings(INSTALLED_APPS=[]):
            importlib.import_module(djangae_urls_name)

        # And finally check that urls was imported, but not the mapreduce libs.
        for name in module_names:
            self.assertNotIn(name, sys.modules)

        self.assertIn(djangae_urls_name, sys.modules)
