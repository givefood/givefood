# Enforce the uniqueness rules the models claim but the database never had.
#
# `manage.py checkschema` found these declared in the models and absent from
# production -- the same run-syncdb story as the missing indexes, except the
# consequence is worse. An index that is not there makes a query slow. A
# uniqueness rule that is not there lets in rows the code assumes cannot exist:
#
#   - SlugRedirect.old_slug feeds dict(slug_redirects); a duplicate silently
#     wins over the other and one redirect just stops working.
#   - WebPushSubscription and WhatsappSubscriber are written with
#     update_or_create, which without the constraint races into duplicate rows
#     and then notifies the same device twice.
#   - PlacePhoto.photo_ref and Place.gbpnid are both treated as identifiers.
#
# THIS CAN FAIL, THOUGH IT CANNOT LOSE DATA. If a table already holds rows that
# violate one of these, CREATE UNIQUE INDEX aborts and the migration rolls
# back, leaving everything as it was. Check first with:
#
#   manage.py checkschema --preflight
#
# which counts the offending rows for every uniqueness rule it finds missing,
# using the same NULL semantics a real unique index would.
#
# Because these run CONCURRENTLY, a failure leaves an INVALID index behind
# under the same name, and a retry then reports that the index already exists.
# --preflight lists any that are lying around, with the DROP to clear them.
#
# state_operations=[] throughout: 0001_initial already carries all of these in
# the migration state, which is exactly why faking it without this would have
# left the state asserting constraints the database does not enforce.

from django.db import migrations


UNIQUE_INDEXES = [
    # givefood_place (gbpnid) is deliberately not here. Production holds 6,449
    # duplicate values, so the index cannot be created until they are cleared;
    # 0010 dedupes and then builds it in the same migration.
    ('givefood_placephoto_photo_ref_uniq', 'givefood_placephoto', '("photo_ref")'),
    ('givefood_slugredirect_old_slug_uniq', 'givefood_slugredirect', '("old_slug")'),
    ('givefood_webpushsub_foodbank_endpoint_uniq', 'givefood_webpushsubscription',
     '("foodbank_id", "endpoint")'),
    ('givefood_whatsappsub_phone_foodbank_uniq', 'givefood_whatsappsubscriber',
     '("phone_number", "foodbank_id")'),
]


def _operations():
    for name, table, columns in UNIQUE_INDEXES:
        yield migrations.RunSQL(
            sql='CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS "%s" ON "%s" %s;' % (
                name, table, columns,
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "%s";' % name,
            state_operations=[],
        )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('givefood', '0006_drop_redundant_hit_index'),
    ]

    operations = list(_operations())
