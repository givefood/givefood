import sys
from os.path import dirname, abspath, join, exists

PROJECT_DIR = dirname(dirname(abspath(__file__)))
SITEPACKAGES_DIR = join(PROJECT_DIR, "sitepackages")
DEV_SITEPACKAGES_DIR = join(SITEPACKAGES_DIR, "dev")
PROD_SITEPACKAGES_DIR = join(SITEPACKAGES_DIR, "prod")
APPENGINE_DIR = join(DEV_SITEPACKAGES_DIR, "google_appengine")


def fix_path(include_dev_libs_path=False):
    """ Insert libs folder(s) and SDK into sys.path. The one(s) inserted last take priority. """
    if include_dev_libs_path:
        if exists(APPENGINE_DIR) and APPENGINE_DIR not in sys.path:
            sys.path.insert(1, APPENGINE_DIR)

        if DEV_SITEPACKAGES_DIR not in sys.path:
            sys.path.insert(1, DEV_SITEPACKAGES_DIR)

    if SITEPACKAGES_DIR not in sys.path:
        sys.path.insert(1, PROD_SITEPACKAGES_DIR)


def get_app_config():
    """Returns the application configuration, creating it if necessary."""
    from django.utils.crypto import get_random_string
    from google.appengine.ext import ndb

    class Config(ndb.Model):
        """A simple key-value store for application configuration settings."""
        secret_key = ndb.StringProperty()

    # Create a random SECRET_KEY
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'

    @ndb.transactional()
    def txn():
        # Get or create the Config in a transaction, so that if it doesn't exist we don't get 2
        # threads creating a Config object and one overwriting the other
        key = ndb.Key(Config, 'config')
        entity = key.get()
        if not entity:
            entity = Config(key=key)
            entity.secret_key = get_random_string(50, chars)
            entity.put()
        return entity
    return txn()


def register_custom_checks():
    from . import checks
    from django.core.checks import register, Tags
    register(checks.check_csp_sources_not_unsafe, Tags.security, deploy=True)
    register(checks.check_session_csrf_enabled, Tags.security)
    register(checks.check_csp_is_not_report_only, Tags.security)
    register(checks.check_cached_template_loader_used, Tags.caches, deploy=True)
