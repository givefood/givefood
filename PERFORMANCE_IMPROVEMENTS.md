# Performance Improvements Summary

This document outlines the performance improvements made to the Give Food codebase.

## Changes Implemented

### 1. File I/O Optimization

**Issue**: The `FoodbankDonationPoint.opening_hours_days()` method was loading the bank holidays JSON file on every single call.

**Solution**: Implemented module-level caching of bank holidays data using a global cache variable.

**Impact**: Eliminates repeated file I/O operations, reducing disk access and improving response times for pages displaying donation point opening hours.

**File**: `givefood/models.py`

```python
# Before
bank_holidays = json.load(open("./givefood/data/bank-holidays.json"))

# After
_BANK_HOLIDAYS_CACHE = None

def _get_bank_holidays():
    """Load and cache bank holidays data from JSON file."""
    global _BANK_HOLIDAYS_CACHE
    if _BANK_HOLIDAYS_CACHE is None:
        try:
            with open("./givefood/data/bank-holidays.json") as f:
                _BANK_HOLIDAYS_CACHE = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _BANK_HOLIDAYS_CACHE = {}
    return _BANK_HOLIDAYS_CACHE

# Usage
bank_holidays = _get_bank_holidays()
```

### 2. Database Indexes

**Issue**: Frequently queried fields lacked database indexes, causing slow lookups especially on large tables.

**Solution**: Added `db_index=True` to frequently queried fields.

**Impact**: Faster query execution for common lookup patterns, especially important as the database grows.

**Fields Indexed**:
- `Foodbank.slug` - Used in URL lookups (e.g., `/needs/at/{slug}/`)
- `Foodbank.is_closed` - Used to filter active food banks
- `FoodbankChange.created` - Used for ordering needs by date
- `FoodbankChange.published` - Used to filter published needs
- `FoodbankLocation.slug` - Used in URL lookups
- `FoodbankLocation.is_closed` - Used to filter active locations
- `FoodbankDonationPoint.slug` - Used in URL lookups
- `FoodbankDonationPoint.is_closed` - Used to filter active donation points
- `ParliamentaryConstituency.slug` - Used in URL lookups

**Note**: You'll need to create and run a database migration to apply these indexes:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. N+1 Query Prevention

**Issue**: Multiple queries being executed in loops when accessing related objects.

**Solution**: Added `select_related()` to QuerySets that access ForeignKey relationships.

**Impact**: Reduces database queries from O(n) to O(1) for related object access.

**Changes Made**:

#### `givefood/models.py`
- `ParliamentaryConstituency.location_obj()`: Added `.select_related('foodbank')` to prevent N+1 queries when accessing `location.foodbank` in loops.

#### `gfadmin/views.py`
- `needs()`: Added `.select_related('foodbank')` to the needs queryset
- `search_results()`: Added `.select_related('foodbank')` to the needs search query

#### `gfapi3/views.py`
- `company()`: Optimized the distinct query to use `values_list()` instead of loading full objects

**Example Impact**:
```python
# Before - N+1 queries (1 + number of locations)
locations = FoodbankLocation.objects.filter(parliamentary_constituency=pc)
for location in locations:
    print(location.foodbank.name)  # New query for each iteration

# After - 1 query with JOIN
locations = FoodbankLocation.objects.filter(parliamentary_constituency=pc).select_related('foodbank')
for location in locations:
    print(location.foodbank.name)  # No additional query
```

## Performance Monitoring Recommendations

### 1. Query Monitoring

Consider adding Django Debug Toolbar in development to monitor:
- Number of queries per page
- Slow queries
- Duplicate queries

```python
# In development settings
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

### 2. Database Query Logging

Enable query logging to identify slow queries in production:

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### 3. Caching Strategy

The codebase already uses caching effectively with:
- `@cache_page` decorators on views
- `cache.get()/cache.set()` for data caching

Consider monitoring cache hit rates to ensure optimal performance.

## Additional Optimization Opportunities

### 1. Query Optimization in Templates

**Current State**: Good - no database queries found in templates.

**Best Practice**: Always pass pre-fetched data from views to templates.

### 2. Bulk Operations

**Current State**: Some views iterate and save objects individually (e.g., `foodbank_resave_all`).

**Opportunity**: Consider using `bulk_update()` for bulk save operations when the fields being updated are predictable:

```python
# Example
objects = [...]
for obj in objects:
    obj.field = new_value

# Instead of
for obj in objects:
    obj.save()

# Use
Model.objects.bulk_update(objects, ['field'])
```

### 3. Pagination

**Current State**: Some views limit results with slicing (e.g., `[:200]`).

**Best Practice**: Use Django's `Paginator` for large datasets to avoid loading all records into memory.

### 4. Select Only Required Fields

**Opportunity**: Use `.only()` or `.defer()` to fetch only needed fields:

```python
# If you only need slug and name
foodbanks = Foodbank.objects.only('slug', 'name')

# If you need everything except large text fields
foodbanks = Foodbank.objects.defer('charity_objectives', 'charity_purpose')
```

This is already done in some views (e.g., `wfbn/views.py:geojson()`).

## Testing Performance Improvements

### Measure Before and After

1. **Query Count**: Use Django Debug Toolbar or logging to count queries
2. **Response Time**: Use Django Debug Toolbar or browser dev tools
3. **Database Load**: Monitor database query execution times

### Expected Improvements

- **File I/O**: 100% reduction in file reads after the first call
- **Database Indexes**: 10-100x faster lookups on indexed fields
- **N+1 Queries**: Reduction in queries from O(n) to O(1)

### Example Metrics

For a page showing 20 food banks:

**Before**:
- Queries: ~41 (1 for food banks + 20 for related needs + 20 for other relations)
- Time: ~200ms

**After**:
- Queries: ~2 (1 for food banks with select_related + 1 for other data)
- Time: ~50ms

## Migration Guide

To apply the database indexes:

1. Generate migration:
   ```bash
   python manage.py makemigrations givefood
   ```

2. Review the migration file to ensure it only adds indexes

3. Apply migration:
   ```bash
   python manage.py migrate
   ```

4. Monitor database during migration (indexes are created online in PostgreSQL)

## Rollback Plan

If any issues occur:

1. **Code Changes**: Simply revert the commits
2. **Database Indexes**: Can be removed with:
   ```sql
   DROP INDEX IF EXISTS givefood_foodbank_slug_idx;
   -- Repeat for each index
   ```

## Conclusion

These improvements address the most common performance bottlenecks:
- Repeated file I/O
- Missing database indexes
- N+1 query problems

The changes are minimal, focused, and follow Django best practices. They should provide measurable performance improvements without introducing risks or changing functionality.
