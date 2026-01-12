# Test Suite Documentation

## Overview

This document describes the test suite for the Give Food Django project.

## Test Structure

The test suite is organized as follows:

### Configuration Files

- **pytest.ini** - Main pytest configuration file
  - Uses `test_settings.py` for Django settings
  - Configured for test discovery patterns
  - Uses `--reuse-db` and `--nomigrations` for faster test runs

- **test_settings.py** - Test-specific Django settings
  - Uses SQLite in-memory database instead of PostgreSQL
  - Disables Sentry for tests
  - Speeds up password hashing for tests

- **conftest.py** - Shared pytest fixtures
  - Provides `client` fixture for HTTP requests
  - Provides `api_client` fixture for API testing

### Test Files

#### givefood/tests/
The givefood app has multiple test files organized in a tests directory:

**test_utils.py** - Unit tests for utility functions in `givefood/func.py`:

- **TestTextUtilities** (12 tests)
  - Text comparison and normalization functions
  - Food bank need text cleaning
  - Letter removal utilities

- **TestGeographicUtilities** (9 tests)
  - UK location validation
  - Miles/meters conversion
  - Distance calculations using Haversine formula

- **TestDiffUtilities** (3 tests)
  - HTML diff generation

- **TestJSONUtilities** (3 tests)
  - GeoJSON parsing and validation

**test_views.py** - Integration tests for main application views:

- **TestHomepage** (1 test)
  - Homepage accessibility (handles empty database gracefully)

- **TestStaticPages** (2 tests)
  - About page
  - API landing page

- **TestFoodbankPages** (2 tests)
  - Needs page
  - Food bank search

#### gfapi2/tests.py
Tests for the API v2 endpoints:

- **TestAPI2Index** (2 tests)
  - API index page accessibility
  - API documentation content

- **TestAPI2Docs** (2 tests)
  - API documentation page
  - Example content

- **TestAPI2Foodbanks** (3 tests)
  - Food banks list endpoint (JSON, XML, GeoJSON formats)

#### gfapi3/tests.py
Tests for the API v3 endpoints:

- **TestAPI3Index** (2 tests)
  - API v3 index page accessibility
  - API v3 content verification

*Note: Company endpoint tests require PostgreSQL and are skipped in SQLite test environments.*

#### gfdash/tests.py
Tests for the dashboard app:

- **TestDashboardIndex** (2 tests)
  - Dashboard index page accessibility

- **TestMostRequestedItems** (4 tests)
  - Most requested items page
  - Days parameter validation

- **TestMostExcessItems** (3 tests)
  - Most excess items page
  - Days parameter validation

- **TestItemCategories** (1 test)
- **TestItemGroups** (1 test)
- **TestWeeklyItemcount** (2 tests)
- **TestArticles** (1 test)
- **TestExcess** (1 test)
- **TestFoodbanksFound** (1 test)
- **TestSupermarkets** (1 test)
- **TestTrussellTrust** (2 tests)
- **TestPricePerKg** (1 test)
- **TestPricePerCalorie** (1 test)
- **TestCharityIncomeExpenditure** (1 test)

*Note: Some dashboard tests require PostgreSQL-specific features and are skipped in SQLite test environments.*

#### gfwrite/tests.py
Tests for the Write to MP tool:

- **TestWriteIndex** (2 tests)
  - Write index page accessibility
  - Postcode form presence

- **TestWriteConstituency** (3 tests)
  - Constituency page with valid/invalid slugs
  - MP information display

- **TestWriteEmail** (1 test)
  - Email page GET request handling

- **TestWriteDone** (3 tests)
  - Done/confirmation page
  - Email parameter handling

#### gfauth/tests.py
Tests for the authentication app:

- **TestSignIn** (2 tests)
  - Sign in page accessibility
  - Template rendering

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

- **Total Tests**: 290
- **Passing**: 278 (with SQLite test database)
- **Skipped**: 1
- **Known Failures**: 11 (PostgreSQL-specific features not available in SQLite)
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

3. **PostgreSQL Extensions**: Tests use SQLite instead of PostgreSQL, so extensions like `django-earthdistance` are disabled during testing.

## Future Enhancements

Potential areas for test expansion:

1. Model tests for database schema and relationships
2. Form validation tests
3. Template rendering tests
4. Authentication and permission tests
5. Background task tests
6. Data migration tests
7. Performance/load tests for API endpoints

## Contributing

When adding new functionality:

1. Ensure all existing tests pass
2. Aim for meaningful test coverage
3. Document complex test scenarios
4. Keep tests fast and independent
