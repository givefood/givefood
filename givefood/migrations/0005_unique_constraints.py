# Declare two uniqueness rules the database has been enforcing on its own.
#
# givefood_foodbank_name_key and givefood_placephoto_place_id_uniq exist on
# production but neither model said unique=True, so Django did not know. The
# practical cost was that a duplicate surfaced as an IntegrityError rather than
# a form validation error, and tests -- which build their schema from the
# models -- happily created duplicates that production would have rejected.
#
# PlacePhoto.place_id in particular is load-bearing: photo_from_place_id() does
# a .get(place_id=...) that only has one row to find because of it.
#
# Written as CREATE UNIQUE INDEX ... IF NOT EXISTS rather than letting
# AlterField emit its own ADD CONSTRAINT, which would have added a second,
# identical unique index alongside the one already there. state_operations
# carries the field change into the migration state either way.

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('givefood', '0004_hand_built_indexes'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS '
                '"givefood_foodbank_name_key" ON "givefood_foodbank" ("name");',
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "givefood_foodbank_name_key";',
            state_operations=[
                migrations.AlterField(
                    model_name='foodbank',
                    name='name',
                    field=models.CharField(max_length=100, unique=True),
                ),
            ],
        ),
        migrations.RunSQL(
            sql='CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS '
                '"givefood_placephoto_place_id_uniq" ON "givefood_placephoto" ("place_id");',
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "givefood_placephoto_place_id_uniq";',
            state_operations=[
                migrations.AlterField(
                    model_name='placephoto',
                    name='place_id',
                    field=models.CharField(blank=True, max_length=1024, null=True, unique=True),
                ),
            ],
        ),
    ]
