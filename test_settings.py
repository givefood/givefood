"""
Test settings for Give Food project.
Uses PostgreSQL for testing, matching production configuration.
"""
import os

from givefood.settings import *

# Use PostgreSQL for tests (matching production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('TEST_DB_NAME', os.environ.get('DB_NAME', 'givefood_test')),
        'USER': os.environ.get('TEST_DB_USER', os.environ.get('DB_USER', 'postgres')),
        'PASSWORD': os.environ.get('TEST_DB_PASS', os.environ.get('DB_PASS', 'postgres')),
        'HOST': os.environ.get('TEST_DB_HOST', os.environ.get('DB_HOST', 'localhost')),
        'PORT': os.environ.get('TEST_DB_PORT', '5432'),
    }
}

# Use local memory cache for tests (allows caching tests to work while being isolated)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Disable Sentry for tests
SENTRY_DSN = None

# Disable external API calls
SECRET_KEY = 'test-secret-key-for-testing-only'

# Allow all hosts in tests
ALLOWED_HOSTS = ['*']

# Speed up password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
