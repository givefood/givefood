# THIRD PARTY
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.migrations.loader import MigrationLoader

# DJANGAE
from djangae.db.migrations.operations import DjangaeMigration


def check_migrations(sender, app_config, verbosity, interactive, using, **kwargs):
    """ Handler for the pre_migrate signal.  Checks that Django operations and Djangae operations
        are not mixed in the same migration file.
    """
    connection = connections[using]
    loader = MigrationLoader(connection)
    app_label = app_config.label
    for app_label_migration_pair, migration in loader.disk_migrations.items():
        # This signal gets called for each app, so for effiency only look at migrations for this app
        if app_label_migration_pair[0] != app_label:
            continue

        has_djangae_migrations = False
        has_non_djangae_migrations = False
        for operation in migration.operations:
            if isinstance(operation, DjangaeMigration):
                has_djangae_migrations = True
            else:
                has_non_djangae_migrations = True
        if has_djangae_migrations and has_non_djangae_migrations:
            raise ImproperlyConfigured(
                "Migration %r has a mixture of Djangae and non-Djangae operations." % migration
            )
