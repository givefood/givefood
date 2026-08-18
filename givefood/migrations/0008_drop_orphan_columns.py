# Drop columns left behind by features that are no longer in the models.
#
# `manage.py checkschema` found these on givefood_foodbank with nothing in any
# model referring to them: a removed food bank grouping feature, and a Twitter
# handle from before the site stopped linking to Twitter. Django has not read
# or written any of them in a long time.
#
# This is the only migration in the chain that touches data, which is why it is
# last: `migrate givefood 0007` gets everything else and leaves this one
# unapplied if you would rather look first.
#
# It does not throw the data away. Every row with anything in any of the four
# columns is copied into givefood_dropped_foodbank_columns first, keyed by food
# bank id, and the reverse operation restores from it. To see what would be
# kept before running anything:
#
#   SELECT count(*) FROM givefood_foodbank
#   WHERE foodbank_group_id IS NOT NULL OR foodbank_group_name IS NOT NULL
#      OR foodbank_group_slug IS NOT NULL OR twitter_handle IS NOT NULL;
#
# Dropping foodbank_group_id also drops its index
# (givefood_foodbank_foodbank_group_id_7ea6dda3) and any foreign key on it,
# which Postgres does as part of DROP COLUMN. If a givefood_foodbankgroup table
# still exists it is left alone -- check for it separately with:
#
#   SELECT to_regclass('givefood_foodbankgroup');
#
# state_operations=[] throughout: the models never declared these fields, so
# the migration state has nothing to remove.

from django.db import migrations


ARCHIVE = "givefood_dropped_foodbank_columns"

COLUMNS = [
    ('foodbank_group_id', 'integer'),
    ('foodbank_group_name', 'varchar(100)'),
    ('foodbank_group_slug', 'varchar(100)'),
    ('twitter_handle', 'varchar(50)'),
]

_names = ", ".join('"%s"' % column for column, _type in COLUMNS)
_any_set = " OR ".join('"%s" IS NOT NULL' % column for column, _type in COLUMNS)


class Migration(migrations.Migration):

    dependencies = [
        ('givefood', '0007_missing_unique_constraints'),
    ]

    operations = [
        # Keep a copy of anything that is actually populated. Runs before any
        # DROP COLUMN below and in the same transaction, so either the whole
        # migration lands or none of it does.
        #
        # Guarded on the columns existing: a database built from 0001 never had
        # them, so on a fresh install there is nothing to archive and the
        # CREATE TABLE AS would fail on the unknown column names.
        migrations.RunSQL(
            sql=(
                "DO $$ BEGIN "
                "IF EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'givefood_foodbank' "
                "AND column_name = 'foodbank_group_id') THEN "
                "EXECUTE 'CREATE TABLE IF NOT EXISTS \"%s\" AS "
                "SELECT \"id\" AS foodbank_id, %s FROM \"givefood_foodbank\" "
                "WHERE %s'; "
                "END IF; END $$;" % (ARCHIVE, _names, _any_set)
            ),
            reverse_sql='DROP TABLE IF EXISTS "%s";' % ARCHIVE,
            state_operations=[],
        ),

        # Reverse-only: refill the columns from the archive. Forward it is a
        # no-op, because the archive is the thing created just above.
        #
        # Django unapplies an operations list back to front, so this has to sit
        # between the archive and the drops: on the way back the ADD COLUMNs
        # run first, then this restore, then the archive table is dropped last.
        # Below the drops it would fire before the columns existed; above the
        # archive it would fire after the archive had gone.
        #
        # Guarded on the archive existing, since a database that had nothing to
        # archive has no table to restore from.
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,
            reverse_sql=(
                "DO $$ BEGIN "
                "IF to_regclass('%s') IS NOT NULL THEN "
                "EXECUTE 'UPDATE \"givefood_foodbank\" f SET %s "
                "FROM \"%s\" a WHERE a.foodbank_id = f.\"id\"'; "
                "END IF; END $$;" % (
                    ARCHIVE,
                    ", ".join('\"%s\" = a.\"%s\"' % (c, c) for c, _t in COLUMNS),
                    ARCHIVE,
                )
            ),
            state_operations=[],
        ),
    ] + [
        migrations.RunSQL(
            sql='ALTER TABLE "givefood_foodbank" DROP COLUMN IF EXISTS "%s";' % column,
            reverse_sql=(
                'ALTER TABLE "givefood_foodbank" '
                'ADD COLUMN IF NOT EXISTS "%s" %s NULL;' % (column, column_type)
            ),
            state_operations=[],
        )
        for column, column_type in COLUMNS
    ]
