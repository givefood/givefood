# Drop idx_foodbankhit_day_hits.
#
# It is btree (day) INCLUDE (hits). foodbankhit_day_foodbank_covering_idx is
# btree (day, foodbank_id) INCLUDE (hits) -- same leading column, same included
# payload -- so it answers everything the narrower one did: the /frag/need-hits/
# sum over a date range, and the homepage's most-viewed group-by. Keeping both
# doubled the write cost on the hit counter, which takes an upsert on every
# food bank page view.
#
# Drops no data. An index is derived from the table, and the reverse below
# rebuilds it exactly.
#
# 0004 no longer creates it, so a database built from scratch never has it and
# this is a no-op there. Only long-lived databases need the drop.

from django.db import migrations


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('givefood', '0005_unique_constraints'),
    ]

    operations = [
        migrations.RunSQL(
            sql='DROP INDEX CONCURRENTLY IF EXISTS "idx_foodbankhit_day_hits";',
            reverse_sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                        '"idx_foodbankhit_day_hits" ON "givefood_foodbankhit" '
                        'USING btree (day) INCLUDE (hits);',
            state_operations=[],
        ),
    ]
