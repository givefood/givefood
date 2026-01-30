# Trigram Indexes for Address Autocomplete

The `/aac/` endpoint uses LIKE queries (via Django ORM's `__icontains`) for searching
places and postcodes. These queries benefit from PostgreSQL's trigram indexes for
performance optimization.

## Required PostgreSQL Setup

### 1. Enable the pg_trgm Extension

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 2. Create GIN Indexes for Trigram Operations

These indexes should be created on the production PostgreSQL database:

```sql
-- Index for place name searches
CREATE INDEX CONCURRENTLY place_name_trgm_idx 
ON givefood_place USING GIN (name gin_trgm_ops);

-- Index for postcode searches  
CREATE INDEX CONCURRENTLY postcode_normalized_trgm_idx 
ON givefood_postcode USING GIN (postcode_normalized gin_trgm_ops);
```

## Benefits

- `gin_trgm_ops` indexes enable fast LIKE queries with leading wildcards (`%query%`)
- Standard B-tree indexes cannot efficiently handle patterns like `ILIKE '%market%'`
- Trigram indexes split text into 3-character sequences for efficient substring matching

## Usage in Code

The address autocomplete view (`givefood/views.py:address_autocomplete`) uses:
- `Place.objects.filter(name__icontains=query)` 
- `Postcode.objects.filter(postcode_normalized__icontains=postcode_query)`

Both queries generate `ILIKE '%query%'` SQL which benefits from the trigram indexes.

## Notes

- Use `CREATE INDEX CONCURRENTLY` to avoid locking the tables during index creation
- The pg_trgm extension is included in PostgreSQL contrib packages
- These indexes are PostgreSQL-specific and won't work with SQLite (used in tests)
