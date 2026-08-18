# Index givefood_crawlitem by (foodbank, start DESC), and drop a duplicate.
#
# The food bank admin page lists a food bank's hundred most recent crawls
# ordered by -start. The only index that led with foodbank_id ordered by
# finish, which cannot answer that, so Postgres bitmap scanned every crawl row
# the food bank had -- 3,859 rows across 3,826 heap blocks for an ordinary one
# -- and top-N sorted them to return a hundred. 46ms, and it grows with every
# crawl. Ordering the same query by -finish, which the existing index does
# serve, takes 0.3ms off the same table. This adds the equivalent for -start,
# and the count on the same tab becomes index-only alongside it.
#
# givefood_crawlitem_foodbank_finish_idx is dropped in the same pass. It is
# btree (foodbank_id, finish DESC), character for character what the declared
# givefood_cr_foodban_0432c9_idx already is, and no migration or model has ever
# asked for it -- it predates `manage.py checkschema` and 0004 did not capture
# it. 111MB on a 660MB table, plus a write on all 2.4M rows' worth of crawl
# inserts, for nothing the other index was not already doing.
#
# Drops no data. An index is derived from the table, and the reverse rebuilds
# it exactly.
#
# CONCURRENTLY throughout, hence atomic = False: givefood_crawlitem is written
# by every crawl, and a plain CREATE INDEX would hold ACCESS EXCLUSIVE over
# 2.4M rows for the length of the build.

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('givefood', '0010_dedupe_places'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                '"crawlitem_foodbank_start_idx" ON "givefood_crawlitem" '
                'USING btree ("foodbank_id", "start" DESC);',
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS '
                        '"crawlitem_foodbank_start_idx";',
            state_operations=[
                migrations.AddIndex(
                    model_name='crawlitem',
                    index=models.Index(fields=['foodbank', '-start'],
                                       name='crawlitem_foodbank_start_idx'),
                ),
            ],
        ),
        # Not in the models, so nothing to carry into the migration state.
        migrations.RunSQL(
            sql='DROP INDEX CONCURRENTLY IF EXISTS '
                '"givefood_crawlitem_foodbank_finish_idx";',
            reverse_sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                        '"givefood_crawlitem_foodbank_finish_idx" ON '
                        '"givefood_crawlitem" USING btree '
                        '("foodbank_id", "finish" DESC);',
            state_operations=[],
        ),
    ]
