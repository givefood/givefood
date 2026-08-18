# Indexes for the columns the site actually looks rows up by.
#
# Every public page, API endpoint and markdown view resolves a food bank by
# slug, and locations and donation points by (foodbank, slug) -- none of which
# were indexed. The (foodbank, name) indexes that were there duplicated the
# unique_together constraint's own index and answered no query, so they go.
#
# Written as SQL with IF NOT EXISTS rather than AddIndexConcurrently because
# foodbank_slug_idx already exists on production by hand; a plain CREATE INDEX
# would abort the whole migration on it. state_operations carries the model
# state forward either way, so `makemigrations --check` stays clean.
#
# CONCURRENTLY throughout: the crawler writes to these tables continuously and
# a plain CREATE INDEX holds an ACCESS EXCLUSIVE lock for its duration.

from django.db import migrations, models


ADD = [
    ('foodbank_slug_idx', 'foodbank', 'givefood_foodbank', ['slug'], '("slug")'),
    ('foodbank_uuid_idx', 'foodbank', 'givefood_foodbank', ['uuid'], '("uuid")'),
    ('foodbank_parlcon_slug_idx', 'foodbank', 'givefood_foodbank',
     ['parliamentary_constituency_slug'], '("parliamentary_constituency_slug")'),
    ('foodbank_modified_idx', 'foodbank', 'givefood_foodbank', ['modified'], '("modified")'),
    ('foodbank_last_need_idx', 'foodbank', 'givefood_foodbank', ['last_need'], '("last_need")'),
    ('foodbank_edited_idx', 'foodbank', 'givefood_foodbank', ['edited'], '("edited")'),

    ('location_foodbank_slug_idx', 'foodbanklocation', 'givefood_foodbanklocation',
     ['foodbank', 'slug'], '("foodbank_id", "slug")'),
    ('location_uuid_idx', 'foodbanklocation', 'givefood_foodbanklocation',
     ['uuid'], '("uuid")'),
    ('location_parlcon_slug_idx', 'foodbanklocation', 'givefood_foodbanklocation',
     ['parliamentary_constituency_slug'], '("parliamentary_constituency_slug")'),

    ('dp_foodbank_slug_idx', 'foodbankdonationpoint', 'givefood_foodbankdonationpoint',
     ['foodbank', 'slug'], '("foodbank_id", "slug")'),
    ('dp_uuid_idx', 'foodbankdonationpoint', 'givefood_foodbankdonationpoint',
     ['uuid'], '("uuid")'),
    ('dp_parlcon_slug_idx', 'foodbankdonationpoint', 'givefood_foodbankdonationpoint',
     ['parliamentary_constituency_slug'], '("parliamentary_constituency_slug")'),

    ('need_need_id_idx', 'foodbankchange', 'givefood_foodbankchange',
     ['need_id'], '("need_id")'),
    ('need_need_id_str_idx', 'foodbankchange', 'givefood_foodbankchange',
     ['need_id_str'], '("need_id_str")'),

    ('parlcon_slug_idx', 'parliamentaryconstituency', 'givefood_parliamentaryconstituency',
     ['slug'], '("slug")'),
]

# Duplicates of the unique_together indexes on the very same columns.
DROP = [
    ('givefood_fo_foodban_f22e7e_idx', 'foodbanklocation',
     'givefood_foodbanklocation', ['foodbank', 'name'], '("foodbank_id", "name")'),
    ('givefood_fo_foodban_148ce5_idx', 'foodbankdonationpoint',
     'givefood_foodbankdonationpoint', ['foodbank', 'name'], '("foodbank_id", "name")'),
]


def _operations():

    for name, model_name, table, fields, columns in DROP:
        yield migrations.RunSQL(
            sql='DROP INDEX CONCURRENTLY IF EXISTS "%s";' % name,
            reverse_sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "%s" ON "%s" %s;' % (
                name, table, columns,
            ),
            state_operations=[
                migrations.RemoveIndex(model_name=model_name, name=name),
            ],
        )

    for name, model_name, table, fields, columns in ADD:
        yield migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "%s" ON "%s" %s;' % (
                name, table, columns,
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "%s";' % name,
            state_operations=[
                migrations.AddIndex(
                    model_name=model_name,
                    index=models.Index(fields=fields, name=name),
                ),
            ],
        )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('givefood', '0002_reconcile_declared_indexes'),
    ]

    operations = list(_operations())
