# -*- coding: utf-8 -*-
import os
from importlib import import_module

from django.db import migrations
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations.base import Operation
from djangae.contrib.contenttypes.models import SimulatedContentTypeManager


class PatchMigrationsOperation(Operation):

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def state_forwards(self, app_label, state):
        """ Patch manager on ModelState during migrations """
        contenttype = state.models[('contenttypes', 'contenttype')]
        contenttype.managers[0] = ('objects', SimulatedContentTypeManager(model=contenttype))


def get_installed_app_labels_with_migrations():
    """ Get the app labels, because settings.INSTALLED_APPS doesn't necessarily give us the labels.
        Remove django.contrib.contenttypes because we want it to run before us.
        Return list of tuples like ('admin', '__first__')
    """
    from django.apps import apps
    apps_with_migrations = []
    for app in apps.get_app_configs():
        if app.label == 'contenttypes':
            continue  # Ignore the contenttypes app

        migrations_module = MigrationLoader.migrations_module(app.label)
        try:
            # Django 1.11 changed the return value of the migrations_module call to a 2-element
            # tuple.  The actual module is the first entry
            if isinstance(migrations_module, tuple):
                migrations_module = migrations_module[0]

            if migrations_module:
                module = import_module(migrations_module)
            else:
                continue
        except ImportError:
            continue

        if not hasattr(module, "__path__"):
            continue

        # Make sure there are python files in the migration folder (other than the init file)
        has_files = any(
            x for x in os.listdir(module.__path__[0]) if x.endswith(".py") and x != "__init__.py"
        )
        if not has_files:
            continue

        apps_with_migrations.append(app.label)

    return [(x, '__first__') for x in apps_with_migrations]


class Migration(migrations.Migration):

    run_before = get_installed_app_labels_with_migrations()

    dependencies = [
        ('contenttypes', '__first__')
    ]

    operations = [
        PatchMigrationsOperation(),
    ]
