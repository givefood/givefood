# Build the indexes that 0001_initial claims exist but production does not have.
#
# The project ran on `migrate --run-syncdb` for years. run-syncdb builds a
# table's indexes when it first creates the table and never touches it again,
# so every Meta.indexes entry added to a model after its table already existed
# was only ever a declaration. Faking 0001_initial onto production records
# those indexes as present, so without this migration the state would say they
# exist and nothing would ever build them.
#
# Confirmed absent from production by `manage.py checkschema`. Written as SQL
# with IF NOT EXISTS rather than AddIndex so it is safe to run against a
# database that has some of them already, and with state_operations=[] because
# 0001_initial has already put them into the migration state.

from django.db import migrations


INDEXES = [
    ('givefood_cr_foodban_0432c9_idx', 'givefood_crawlitem', '("foodbank_id", "finish" DESC)'),
    ('givefood_fo_foodban_74bf0e_idx', 'givefood_foodbankarticle', '("foodbank_id", "published_date" DESC)'),
    ('givefood_pl_populat_cbda9b_idx', 'givefood_place', '("population" DESC, "name")'),
    ('givefood_fo_foodban_cdb8c9_idx', 'givefood_foodbankchange', '("foodbank_id", "created" DESC)'),
    ('givefood_fo_publish_d6429b_idx', 'givefood_foodbankchange', '("published", "foodbank_id")'),
    ('givefood_or_foodban_0f7e2c_idx', 'givefood_order', '("foodbank_id", "delivery_datetime" DESC)'),
    ('givefood_fo_foodban_a91527_idx', 'givefood_foodbanksubscriber', '("foodbank_id", "confirmed")'),
    ('givefood_we_foodban_b5fd48_idx', 'givefood_webpushsubscription', '("foodbank_id", "created" DESC)'),
    ('givefood_mo_foodban_86abe1_idx', 'givefood_mobilesubscriber', '("foodbank_id", "created" DESC)'),
    ('givefood_wh_foodban_0d6c2f_idx', 'givefood_whatsappsubscriber', '("foodbank_id", "created" DESC)'),
]


def _operations():
    for name, table, columns in INDEXES:
        yield migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "%s" ON "%s" %s;' % (
                name, table, columns,
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "%s";' % name,
            state_operations=[],
        )


class Migration(migrations.Migration):

    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
    atomic = False

    dependencies = [
        ('givefood', '0001_initial'),
    ]

    operations = list(_operations())
