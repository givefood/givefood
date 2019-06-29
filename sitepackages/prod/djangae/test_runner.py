import unittest
import os
from unittest import TextTestResult

from django.test.runner import DiscoverRunner
from django.db import NotSupportedError

from djangae import environment

from google.appengine.ext import testbed


# Many Django tests require saving instances with a PK
# of zero. App Engine doesn't allow this (it treats the key
# as incomplete in this case) so we skip those tests here
DJANGO_TESTS_WHICH_REQUIRE_ZERO_PKS = {
    'model_forms.tests.ModelMultipleChoiceFieldTests.test_model_multiple_choice_required_false',
    'model_forms.tests.ModelChoiceFieldTests.test_modelchoicefield',
    'custom_pk.tests.CustomPKTests.test_zero_non_autoincrement_pk',
    'bulk_create.tests.BulkCreateTests.test_zero_as_autoval'
}

# These tests only work if you haven't changed AUTH_USER_MODEL
# This is probably a bug in Django (the tests should use skipIfCustomUser)
# but I haven't had a chance to see if it's fixed in master (and it's not fixed in
# 1.7, so this needs to exist either way)
DJANGO_TESTS_WHICH_REQUIRE_AUTH_USER = {
    'proxy_models.tests.ProxyModelAdminTests.test_cascade_delete_proxy_model_admin_warning',
    'proxy_models.tests.ProxyModelAdminTests.test_delete_str_in_model_admin',
    'proxy_models.tests.ProxyModelTests.test_permissions_created' # Requires permissions created
}

DJANGO_TESTS_WHICH_HAVE_BUGS = {
    'one_to_one.tests.OneToOneTests.test_foreign_key', # Uses the wrong IDs, fixed in 1.8+
}

# This is potentially fixable by us. sql_with_params returns a tuple of
# our Select/Insert/UpdateCommand, and an empty list (because the params
# are stored in the where tree. Some tests assume that we'll be returning the
# params separately, and so they fail. We could fix this by actually returning the
# values that went into the where, but that's for another day.
DJANGO_TESTS_WHICH_EXPECT_SQL_PARAMS = {
    'model_forms.tests.ModelMultipleChoiceFieldTests.test_clean_does_deduplicate_values',
    'ordering.tests.OrderingTests.test_order_by_f_expression_duplicates'
}


# Django 1.8 removed the supports_select_related flag, so we have to manually skip
# tests which depend on it
DJANGO_TESTS_WHICH_USE_SELECT_RELATED = {
    'defer.tests.DeferTests.test_defer_with_select_related',
    'defer.tests.DeferTests.test_defer_select_related_raises_invalid_query',
    'defer.tests.DeferTests.test_only_select_related_raises_invalid_query',
    'defer.tests.DeferTests.test_only_with_select_related',
    'model_inheritance.tests.ModelInheritanceDataTests.test_select_related_works_on_parent_model_fields'
}


DJANGO_TESTS_TO_SKIP = DJANGO_TESTS_WHICH_REQUIRE_ZERO_PKS.union(
    DJANGO_TESTS_WHICH_REQUIRE_AUTH_USER).union(
    DJANGO_TESTS_WHICH_HAVE_BUGS).union(
    DJANGO_TESTS_WHICH_EXPECT_SQL_PARAMS).union(
    DJANGO_TESTS_WHICH_USE_SELECT_RELATED
)

def init_testbed():
    # We don't initialize the datastore stub here, that needs to be done by Django's create_test_db and destroy_test_db.
    IGNORED_STUBS = [ "init_datastore_v3_stub" ]

    stub_kwargs = {
        "init_taskqueue_stub": {
            "root_path": environment.get_application_root()
        }
    }
    bed = testbed.Testbed()
    bed.activate()
    for init_name in testbed.INIT_STUB_METHOD_NAMES.values():
        if init_name in IGNORED_STUBS:
            continue

        getattr(bed, init_name)(**stub_kwargs.get(init_name, {}))

    return bed


def bed_wrap(test):
    def _wrapped(*args, **kwargs):
        bed = None
        try:
            # Init test stubs
            bed = init_testbed()

            return test(*args, **kwargs)
        finally:
            if bed:
                bed.deactivate()
                bed = None

    return _wrapped


class SkipUnsupportedTestResult(TextTestResult):
    def addError(self, test, err):
        skip = os.environ.get("SKIP_UNSUPPORTED", True)
        # If the error is a NotSupportedError and the test is a Django test (where we expect some
        # functionality to be unsupported) rather than a Djangae test (where our tests should be
        # written to explicitly state which things are and aren't supported) then skip it
        if skip and err[0] in (NotSupportedError,) and test.__module__.split(".")[0] != "djangae":
            self.addExpectedFailure(test, err)
        else:
            super(SkipUnsupportedTestResult, self).addError(test, err)


class DjangaeTestSuiteRunner(DiscoverRunner):
    def _discover_additional_tests(self):
        """
            Django's DiscoverRunner only detects apps that are below
            manage.py, which isn't particularly useful if you have other apps
            on the path that need testing (arguably all INSTALLED_APPS should be tested
            as they all form part of your project and a bug in them could bring your site down).

            This method looks for a setting called DJANGAE_ADDITIONAL_TEST_APPS in
            and will add extra test cases found in those apps. By default this adds the
            djangae tests to your app, but you can of course override that.
        """
        from django.conf import settings
        from importlib import import_module

        ADDITIONAL_APPS = getattr(settings, "DJANGAE_ADDITIONAL_TEST_APPS", ("djangae",))
        extra_tests = []
        for app in ADDITIONAL_APPS:
            mod = import_module(app)
            if mod:
                folder = mod.__path__[0]
                new_tests = self.test_loader.discover(start_dir=folder, top_level_dir=os.path.dirname(folder))

                extra_tests.extend(new_tests._tests)
                self.test_loader._top_level_dir = None
        return extra_tests


    def build_suite(self, *args, **kwargs):
        extra_tests = self._discover_additional_tests()
        args = list(args)
        args[1] = extra_tests
        suite = super(DjangaeTestSuiteRunner, self).build_suite(*args, **kwargs)

        new_tests = []

        # Django's DiscoveryRunner can create duplicate tests when passing
        # extra_tests argument. Getting rid of that:
        suite._tests = list(set(suite._tests))

        for i, test in enumerate(suite._tests):

            # https://docs.djangoproject.com/en/1.7/topics/testing/advanced/#django.test.TransactionTestCase.available_apps
            # available_apis is part of an internal API that allows to speed up
            # internal Django test,  but that breaks the integration with
            # Djangae models and tests, so we are disabling it here
            if hasattr(test, 'available_apps'):
                test.available_apps = None

            if args[0] and not any([test.id().startswith(x) for x in args[0]]):
                continue

            if test.id() in DJANGO_TESTS_TO_SKIP:
                continue #FIXME: It would be better to wrap this in skipTest or something

            new_tests.append(bed_wrap(test))

        suite._tests[:] = new_tests

        return suite


class SkipUnsupportedRunner(DjangaeTestSuiteRunner):
    def run_suite(self, suite, **kwargs):
        return unittest.TextTestRunner(
            verbosity=self.verbosity,
            failfast=self.failfast,
            resultclass=SkipUnsupportedTestResult
        ).run(suite)
