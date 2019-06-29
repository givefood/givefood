from nose.plugins import Plugin
from djangae.test_runner import init_testbed


class DjangaePlugin(Plugin):
    enabled = True
    def configure(self, options, conf):
        pass

    def startTest(self, test):
        self.bed = init_testbed()

    def stopTest(self, test):
        self.bed.deactivate()
