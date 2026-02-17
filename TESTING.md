# Test Suite Documentation

## Overview

This document describes the test suite for the Give Food Django project.

## Test Structure

The test suite is organized as follows:

### Configuration Files

- **pyproject.toml** `[tool.pytest.ini_options]` - Main pytest configuration
  - Uses `test_settings.py` for Django settings
  - Configured for test discovery patterns
  - Uses `--reuse-db` and `--nomigrations` for faster test runs

- **test_settings.py** - Test-specific Django settings
  - Uses PostgreSQL database matching production configuration
  - Disables Sentry for tests
  - Speeds up password hashing for tests

- **conftest.py** - Shared pytest fixtures
  - Provides `client` fixture for HTTP requests
  - Provides `api_client` fixture for API testing

### Test Files

#### givefood/tests/
The givefood app has multiple test files organized in a tests directory:

**test_utils.py** - Unit tests for utility functions in `givefood/func.py`:
- Text comparison and normalization functions
- Geographic utilities (UK location validation, distance calculations)
- HTML diff generation
- GeoJSON parsing and validation
- User IP detection
- Plus code handling

**test_views.py** - Integration tests for main application views:
- Homepage, static pages, food bank pages
- Sitemap, manifest, llms.txt
- Country pages
- Fragment views, WhatsApp webhook
- Address autocomplete
- Markdown pages

**test_postcode.py** - Postcode model and import command tests

**test_foodbank_article.py** - Food bank article title capitalisation tests

**test_foodbank_bounds.py** - Food bank geographic bounds tests

**test_foodbank_change.py** - Food bank change translation and text tests

**test_foodbank_service_area.py** - Food bank service area tests

**test_slug_redirect.py** - Slug redirect model, caching, and URL tests

**test_order.py** - Order model and nullable food bank tests

**test_dump_model.py** - Data dump model tests

**test_mobile_location.py** - Mobile location tests

**test_opening_hours_days.py** - Opening hours and days tests

**test_credentials_caching.py** - Credentials caching tests

**test_template_tags.py** - Custom template tag tests

**test_async_notifications.py** - Async task priority and delegation tests

**test_firebase_notifications.py** - Firebase notification tests

**test_middleware.py** - GeoJSON preload, GZip, and render time middleware tests

#### gfadmin/tests/
The admin app has an extensive test suite across 27 test files covering:
- Food bank management (check, touch, URLs, partial forms, photos, social media, crawl display, tab icons)
- Need views and categorisation
- Crawl sets (view, navigation, time taken)
- Search functionality
- Slug redirect admin
- HTMX delete operations
- Index and settings views
- Subscriptions and article management
- Task statistics
- AI detail views
- Fragment endpoints
- Food bank location area forms
- N+1 query prevention

#### gfapi2/tests.py
Tests for the API v2 endpoints covering index, documentation, food banks, food bank detail, needs, locations, and parliamentary constituency endpoints.

#### gfapi3/tests.py
Tests for the API v3 endpoints:
- API v3 index page accessibility and content verification

*Note: Company endpoint tests use PostgreSQL's DISTINCT ON feature.*

#### gfdash/tests.py
Tests for the dashboard app covering index, most requested items, most excess items, item categories, item groups, weekly item count, articles, excess, food banks found, supermarkets, Trussell Trust, price per kg, price per calorie, and charity income/expenditure views.

*Note: Some dashboard tests use PostgreSQL-specific features like `to_char`.*

#### gfwfbn/tests.py
Tests for the What Food Banks Need tool covering index, food bank pages, location pages, search, donation points, nearby food banks, news pages, charity pages, markdown pages, GeoJSON endpoints, and subscription pages.

#### gfdumps/tests.py
Tests for the data dumps app covering index page, dump list, dump format, and CSV content.

#### gfwrite/tests.py
Tests for the Write to MP tool covering index, constituency pages, email handling, and done/confirmation pages.

#### gfauth/tests.py
Tests for the authentication app covering sign in page accessibility and template rendering.

*Note: Sign out and OAuth receiver tests require session data/credentials and are skipped.*

## Running Tests

### Basic Usage

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest givefood/tests/test_utils.py

# Run specific test class
uv run pytest givefood/tests/test_utils.py::TestTextUtilities

# Run specific test
uv run pytest givefood/tests/test_utils.py::TestTextUtilities::test_text_for_comparison_lowercase
```

### Coverage Reports

```bash
# Generate coverage report
uv run pytest --cov=givefood --cov=gfapi2

# Generate HTML coverage report
uv run pytest --cov=givefood --cov=gfapi2 --cov-report=html
```

## Test Statistics

- **Total Tests**: ~500
- **Coverage Areas**:
  - Text processing utilities
  - Geographic calculations
  - API endpoints (v2 and v3)
  - View accessibility
  - JSON/GeoJSON handling
  - Dashboard views
  - Write to MP tool
  - Authentication pages
  - Data dumps
  - Admin tool views and forms
  - What Food Banks Need pages
  - Middleware
  - Models (postcodes, orders, food bank articles, slug redirects)
  - Template tags
  - Background tasks and notifications

## Test Approach

### Unit Tests
- Test individual functions in isolation
- Focus on edge cases and boundary conditions
- No external API calls or database dependencies

### Integration Tests
- Test Django views and API endpoints
- Use Django test client
- Test with empty database (realistic for CI/CD)
- Allow for graceful failures when database is empty

### Fixtures
- Use pytest fixtures for test client setup
- Reuse database between tests for speed
- Skip migrations during tests

## Known Limitations

1. **Empty Database Testing**: Some views (like the homepage) expect database data and will fail gracefully with an empty database. Tests are designed to handle this.

2. **External APIs**: Tests do not call external APIs (geocoding, maps, etc.) to avoid dependencies and rate limits.

3. **PostgreSQL Extensions**: Tests run against PostgreSQL with `cube` and `earthdistance` extensions, matching production configuration.

## Future Enhancements

Potential areas for test expansion:

1. Data migration tests
2. Performance/load tests for API endpoints

## Contributing

When adding new functionality:

1. Ensure all existing tests pass
2. Aim for meaningful test coverage
3. Document complex test scenarios
4. Keep tests fast and independent
