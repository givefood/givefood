from django.db import migrations


class Migration(migrations.Migration):
    """Make autovacuum reach these tables before their visibility maps go stale.

    None of these had ever been vacuumed. givefood_postcode was reporting zero
    live rows against an actual 1,796,701, and givefood_crawlitem 50,057 against
    2,519,060.

    Postgres triggers an insert-driven autovacuum at
    autovacuum_vacuum_insert_threshold + scale_factor * live_rows. At the 0.2
    default that is a fifth of the table, which on tables this size is millions of
    rows - so the visibility map stayed empty for months and index-only scans
    degraded into full heap fetches. On opencharities the measured effect was an
    index-only scan doing one heap fetch per row (805,586 of them) and losing to a
    sequential scan; after a manual VACUUM the same query went 3,504ms -> 429ms.

    The ANALYZE half mattered as much: several of these tables were feeding the
    planner row estimates out by 10-450x.

    0.05 makes the trigger fire roughly four times sooner. It does not immunise
    against a pg_stat_reset(), which zeroes n_ins_since_vacuum and is what let
    these drift in the first place - it just shortens the window.

    ALTER TABLE ... SET (reloptions) is a catalog-only change and takes only a
    brief ACCESS EXCLUSIVE lock, so this needs no CONCURRENTLY treatment.
    """

    dependencies = [
        ('givefood', '0011_crawlitem_foodbank_start_index'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE givefood_placephoto SET (autovacuum_vacuum_insert_scale_factor = 0.05);",
            reverse_sql="ALTER TABLE givefood_placephoto RESET (autovacuum_vacuum_insert_scale_factor);",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE givefood_crawlitem SET (autovacuum_vacuum_insert_scale_factor = 0.05);",
            reverse_sql="ALTER TABLE givefood_crawlitem RESET (autovacuum_vacuum_insert_scale_factor);",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE givefood_postcode SET (autovacuum_vacuum_insert_scale_factor = 0.05);",
            reverse_sql="ALTER TABLE givefood_postcode RESET (autovacuum_vacuum_insert_scale_factor);",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE givefood_place SET (autovacuum_vacuum_insert_scale_factor = 0.05);",
            reverse_sql="ALTER TABLE givefood_place RESET (autovacuum_vacuum_insert_scale_factor);",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE givefood_foodbankchangeline SET (autovacuum_vacuum_insert_scale_factor = 0.05);",
            reverse_sql="ALTER TABLE givefood_foodbankchangeline RESET (autovacuum_vacuum_insert_scale_factor);",
        ),
    ]
