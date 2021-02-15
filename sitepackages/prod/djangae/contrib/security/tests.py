import logging

from djangae.test import TestCase
from djangae.contrib.security.management.commands import dumpurls


class DumpUrlsTests(TestCase):
    def test_dumpurls(self):
        """ Test that the `dumpurls` command runs without dying. """
        logging.debug('%s', "*" * 50)
        command = dumpurls.Command()
        command.handle()
