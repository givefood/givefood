# Generated migration for database cache table

from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    """Create the cache table using Django's createcachetable command."""
    call_command("createcachetable", verbosity=0, interactive=False)


def drop_cache_table(apps, schema_editor):
    """Drop the cache table."""
    schema_editor.execute("DROP TABLE IF EXISTS givefood_cache_table")


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(create_cache_table, reverse_code=drop_cache_table),
    ]
