# Remove duplicate Place rows, then enforce the uniqueness the model declares.
#
# Place.gbpnid says unique=True but production has 6,449 duplicate values. The
# cause is import_places, which bulk_creates without any get_or_create or
# uniqueness check -- so running the import a second time inserted the whole
# dataset again, and there was no constraint in the database to stop it.
#
# The visible effects are duplicate URLs in the places sitemap and several rows
# sitting behind each place page, where the view does .first() and silently
# picks one.
#
# NOTHING IS THROWN AWAY. Every row this removes is copied into
# givefood_dropped_places first, and the reverse puts them all back. The row
# kept for each gbpnid is the one with the lowest id, i.e. the earliest import.
#
# Check the duplicates really are duplicates before running this -- if the
# following returns 0, every set is identical apart from id and timestamps:
#
#   SELECT count(*) FROM (
#       SELECT gbpnid FROM givefood_place GROUP BY gbpnid
#       HAVING count(DISTINCT (name, lat_lng, county, name_slug, county_slug)) > 1
#   ) d;
#
# The unique index is built here rather than in 0007 because it cannot exist
# until the duplicates are gone, and 0007 runs first.
#
# atomic = False for CREATE INDEX CONCURRENTLY, so the three steps commit
# separately. Each is written to be re-runnable: the archive is IF NOT EXISTS,
# and the delete is keyed off the archive, so an interrupted run finishes
# correctly when it is repeated.

from django.db import migrations


# Read by `checkschema --preflight`, so the duplicates it finds are reported
# as handled here rather than as a blocker you have to clear by hand first.
REPAIRS = [("givefood_place", ["gbpnid"])]

ARCHIVE = "givefood_dropped_places"
INDEX = "givefood_place_gbpnid_uniq"


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('givefood', '0009_repair_charityyear_pk'),
    ]

    operations = [
        # 1. Copy every row that is about to go.
        migrations.RunSQL(
            sql=(
                'CREATE TABLE IF NOT EXISTS "%s" AS '
                'SELECT * FROM "givefood_place" WHERE "id" NOT IN '
                '(SELECT min("id") FROM "givefood_place" GROUP BY "gbpnid");'
                % ARCHIVE
            ),
            reverse_sql='DROP TABLE IF EXISTS "%s";' % ARCHIVE,
            state_operations=[],
        ),

        # 2. Delete them, driven off the archive so a repeat run finishes the
        #    job rather than computing a different set.
        migrations.RunSQL(
            sql=(
                'DELETE FROM "givefood_place" WHERE "id" IN '
                '(SELECT "id" FROM "%s");' % ARCHIVE
            ),
            # Reverse runs after the index has been dropped by the operation
            # below, so the rows can go back in without tripping over it.
            reverse_sql=(
                'INSERT INTO "givefood_place" SELECT * FROM "%s";' % ARCHIVE
            ),
            state_operations=[],
        ),

        # 3. Now it can be enforced.
        migrations.RunSQL(
            sql=(
                'CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS "%s" '
                'ON "givefood_place" ("gbpnid");' % INDEX
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "%s";' % INDEX,
            state_operations=[],
        ),
    ]
