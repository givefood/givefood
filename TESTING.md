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

## Running Tests

### Basic Usage

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest givefood/tests/test_utils.py

# Run specific test class
pytest givefood/tests/test_utils.py::TestTextUtilities

# Run specific test
pytest givefood/tests/test_utils.py::TestTextUtilities::test_text_for_comparison_lowercase
```

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=givefood --cov=gfapi2

# Generate HTML coverage report
pytest --cov=givefood --cov=gfapi2 --cov-report=html
```

## Test Statistics

- **Total Tests**: 39
- **Passing**: 39 (100%)
- **Coverage Areas**:
  - Text processing utilities
  - Geographic calculations
  - API endpoints
  - View accessibility
  - JSON/GeoJSON handling

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
