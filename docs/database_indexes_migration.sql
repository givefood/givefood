# Database Index Migration SQL

# This file contains the SQL statements to add database indexes for performance improvements.
# These indexes correspond to the db_index=True fields added to the Django models.

# Note: These are PostgreSQL-specific statements. Adjust if using a different database.

# Run these statements when you're ready to apply the indexes.
# Indexes are created CONCURRENTLY in PostgreSQL to avoid locking tables during creation.

# Foodbank indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS givefood_foodbank_slug_idx 
ON givefood_foodbank (slug);

CREATE INDEX CONCURRENTLY IF NOT EXISTS givefood_foodbank_is_closed_idx 
ON givefood_foodbank (is_closed);

# FoodbankChange indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS givefood_foodbankchange_created_idx 
ON givefood_foodbankchange (created);

CREATE INDEX CONCURRENTLY IF NOT EXISTS givefood_foodbankchange_published_idx 
ON givefood_foodbankchange (published);

# FoodbankLocation indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS givefood_foodbanklocation_slug_idx 
ON givefood_foodbanklocation (slug);

CREATE INDEX CONCURRENTLY IF NOT EXISTS givefood_foodbanklocation_is_closed_idx 
ON givefood_foodbanklocation (is_closed);

# FoodbankDonationPoint indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS givefood_foodbankdonationpoint_slug_idx 
ON givefood_foodbankdonationpoint (slug);

CREATE INDEX CONCURRENTLY IF NOT EXISTS givefood_foodbankdonationpoint_is_closed_idx 
ON givefood_foodbankdonationpoint (is_closed);

# ParliamentaryConstituency indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS givefood_parliamentaryconstituency_slug_idx 
ON givefood_parliamentaryconstituency (slug);

# To verify indexes were created, run:
# SELECT tablename, indexname FROM pg_indexes WHERE schemaname = 'public' AND tablename LIKE 'givefood_%' ORDER BY tablename, indexname;

# To rollback (remove indexes), run:
# DROP INDEX CONCURRENTLY IF EXISTS givefood_foodbank_slug_idx;
# DROP INDEX CONCURRENTLY IF EXISTS givefood_foodbank_is_closed_idx;
# DROP INDEX CONCURRENTLY IF EXISTS givefood_foodbankchange_created_idx;
# DROP INDEX CONCURRENTLY IF EXISTS givefood_foodbankchange_published_idx;
# DROP INDEX CONCURRENTLY IF EXISTS givefood_foodbanklocation_slug_idx;
# DROP INDEX CONCURRENTLY IF EXISTS givefood_foodbanklocation_is_closed_idx;
# DROP INDEX CONCURRENTLY IF EXISTS givefood_foodbankdonationpoint_slug_idx;
# DROP INDEX CONCURRENTLY IF EXISTS givefood_foodbankdonationpoint_is_closed_idx;
# DROP INDEX CONCURRENTLY IF EXISTS givefood_parliamentaryconstituency_slug_idx;
