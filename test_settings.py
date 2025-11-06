"""
Test settings for Give Food project.
Uses SQLite for testing instead of PostgreSQL.
"""
from givefood.settings import *

# Use SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable django-earthdistance for tests since SQLite doesn't support it
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'django_earthdistance']

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

# Use LocMemCache for tests (faster than DatabaseCache)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}
