# Capture the indexes that were built by hand directly on production.
#
# `manage.py checkschema` found these in the database with nothing in the code
# declaring them. They were created by hand over the years -- several of them
# are the ones that made the nearest-location queries fast -- so a database
# rebuilt from migrations (CI, a new dev box, a restore onto empty) would come
# up without them and quietly perform nothing like production.
#
# They are recorded as raw SQL rather than Meta.indexes for two reasons:
#
#   - ll_to_earth() cannot be expressed as a models.Index at all.
#   - Django caps index names at 30 characters, and most of these are longer.
#     Renaming them would mean dropping and rebuilding on live tables for no
#     functional gain.
#
# state_operations=[] throughout: the models do not declare them, so the
# migration state must not either, otherwise makemigrations would try to drop
# them on the next run.
#
# IF NOT EXISTS so this is a no-op against production, where they already are.

from django.db import migrations


INDEXES = [
    # -- earthdistance GiST. These are what the KNN <-> ordering in
    # -- givefood.utils.geo.NearestFirst resolves against; without them the
    # -- nearest-location queries fall back to a seq scan per request.
    ('foodbank_earth_open_idx', 'givefood_foodbank',
     'USING gist (ll_to_earth(latitude, longitude)) WHERE (is_closed = false)'),
    ('idx_foodbanklocation_earthdistance_open', 'givefood_foodbanklocation',
     'USING gist (ll_to_earth(latitude, longitude)) WHERE (is_closed = false)'),
    ('idx_foodbankdonationpoint_earthdistance_open', 'givefood_foodbankdonationpoint',
     'USING gist (ll_to_earth(latitude, longitude)) WHERE (is_closed = false)'),

    # -- Foodbank
    ('foodbank_closed_edited_desc_idx', 'givefood_foodbank',
     'USING btree (is_closed, edited DESC)'),
    ('idx_foodbank_lat_lng', 'givefood_foodbank',
     'USING btree (latitude, longitude)'),

    # -- Needs
    ('idx_foodbankchange_published_created', 'givefood_foodbankchange',
     'USING btree (published, created DESC) WHERE (published = true)'),
    ('fcl_need_cat_type', 'givefood_foodbankchangeline',
     'USING btree (need_id, category, type)'),
    ('changeline_type_idx', 'givefood_foodbankchangeline',
     'USING btree (type)'),
    ('translation_need_lang_idx', 'givefood_foodbankchangetranslation',
     'USING btree (need_id, language)'),
    ('foodbankdiscrepancy_status_created_idx', 'givefood_foodbankdiscrepancy',
     'USING btree (status, created DESC)'),

    # -- Donation points
    ('idx_donationpoint_is_closed', 'givefood_foodbankdonationpoint',
     'USING btree (is_closed)'),
    ('idx_givefood_foodbankdonationpoint_company_slug_name', 'givefood_foodbankdonationpoint',
     'USING btree (company_slug, name)'),

    # -- Hit counter
    # idx_foodbankhit_day_hits -- btree (day) INCLUDE (hits) -- is deliberately
    # not here. It is a strict prefix of the covering index below, which serves
    # every query it did. 0007 drops it from databases that already have it.
    ('foodbankhit_day_foodbank_covering_idx', 'givefood_foodbankhit',
     'USING btree (day, foodbank_id) INCLUDE (hits)'),

    # -- Everything else
    ('idx_charityyear_foodbank_date', 'givefood_charityyear',
     'USING btree (foodbank_id, date DESC)'),
    ('crawlitem_content_type_object_idx', 'givefood_crawlitem',
     'USING btree (content_type_id, object_id)'),
    ('crawlitem_finish_idx', 'givefood_crawlitem',
     'USING btree (finish)'),
    ('idx_dump_type_format_created', 'givefood_dump',
     'USING btree (dump_type, dump_format, created DESC)'),
    ('idx_foodbankarticle_featured_published', 'givefood_foodbankarticle',
     'USING btree (featured, published_date DESC) WHERE (featured = true)'),
]


def _operations():
    for name, table, definition in INDEXES:
        yield migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "%s" ON "%s" %s;' % (
                name, table, definition,
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "%s";' % name,
            state_operations=[],
        )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('givefood', '0003_lookup_indexes'),
    ]

    operations = list(_operations())
