# SlugRedirect Model

This document explains the SlugRedirect model that replaces the hard-coded OLD_FOODBANK_SLUGS dictionary.

## Overview

The `SlugRedirect` model provides a database-backed solution for managing URL redirects for food bank slugs. This allows redirects to be managed dynamically without requiring code changes.

## Model Structure

```python
class SlugRedirect(models.Model):
    old_slug = models.CharField(max_length=200, unique=True, db_index=True)
    new_slug = models.CharField(max_length=200, db_index=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
```

## Usage

### Adding a New Redirect

Use Django shell to add a new redirect:

```python
from givefood.models import SlugRedirect
from django.core.cache import cache

# Create a new redirect
SlugRedirect.objects.create(
    old_slug="old-foodbank-name",
    new_slug="new-foodbank-name"
)

# Clear the cache to make it take effect immediately
cache.delete('slug_redirects_dict')
```

### Viewing All Redirects

```python
from givefood.models import SlugRedirect

# Get all redirects
redirects = SlugRedirect.objects.all()

# Filter by old slug
redirect = SlugRedirect.objects.get(old_slug="angus")
print(f"Redirects to: {redirect.new_slug}")
```

### Updating a Redirect

```python
from givefood.models import SlugRedirect
from django.core.cache import cache

# Update an existing redirect
redirect = SlugRedirect.objects.get(old_slug="old-name")
redirect.new_slug = "updated-new-name"
redirect.save()

# Clear the cache
cache.delete('slug_redirects_dict')
```

### Deleting a Redirect

```python
from givefood.models import SlugRedirect
from django.core.cache import cache

# Delete a redirect
SlugRedirect.objects.filter(old_slug="old-name").delete()

# Clear the cache
cache.delete('slug_redirects_dict')
```

## Caching

Redirects are cached for 1 hour (3600 seconds) to minimize database queries. The cache key is `slug_redirects_dict`.

### Cache Behavior

- **First request**: Queries database and caches results
- **Subsequent requests**: Serves from cache (no database query)
- **After 1 hour**: Cache expires, next request queries database again
- **Manual invalidation**: Use `cache.delete('slug_redirects_dict')` when adding/updating redirects

## URL Pattern Generation

The redirects are used to generate URL patterns for:

1. Main food bank pages: `/needs/at/{old_slug}/` → `/needs/at/{new_slug}/`
2. Subpages: `/needs/at/{old_slug}/{subpage}/` → `/needs/at/{new_slug}/{subpage}/`
3. Welsh versions: `/cy/needs/at/{old_slug}/` → `/cy/needs/at/{new_slug}/`

Where subpages include: locations, news, politics, donationpoints, socialmedia, nearby, subscribe, charity

## Migration

When deploying this change, run:

```bash
python manage.py migrate
```

This will:
1. Create the `givefood_slugredirect` table
2. Populate it with the 54 existing slug redirects from OLD_FOODBANK_SLUGS

## Benefits

- **Dynamic Management**: Add/edit redirects without code changes
- **Performance**: 1-hour caching reduces database load
- **Auditability**: Timestamps track when redirects were created/modified
- **Maintainability**: No hard-coded data in Python files
- **Scalability**: Easy to add redirects as food banks merge or rename

## Database Schema

```sql
CREATE TABLE givefood_slugredirect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    old_slug VARCHAR(200) NOT NULL UNIQUE,
    new_slug VARCHAR(200) NOT NULL,
    created DATETIME NOT NULL,
    modified DATETIME NOT NULL
);

CREATE INDEX givefood_slugredirect_old_slug ON givefood_slugredirect (old_slug);
CREATE INDEX givefood_slugredirect_new_slug ON givefood_slugredirect (new_slug);
```

## Testing

Run the test suite to verify functionality:

```bash
python -m pytest givefood/tests/test_slug_redirect.py -v
```

Tests cover:
- Model creation and uniqueness constraints
- Database querying
- Cache population and retrieval
- Cache invalidation
