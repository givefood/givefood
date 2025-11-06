"""
Tests for cache configuration and functionality.
"""
import pytest
from django.core.cache import cache
from django.core.cache.backends.locmem import LocMemCache
from django.conf import settings


class TestCacheConfiguration:
    """Test cache configuration is properly set up."""

    def test_cache_backend_configured(self):
        """Test that cache backend is configured (not DummyCache)."""
        # In test environment, should be LocMemCache (from test_settings.py)
        assert isinstance(cache, LocMemCache)
        assert settings.CACHES['default']['BACKEND'] == 'django.core.cache.backends.locmem.LocMemCache'

    def test_cache_basic_operations(self):
        """Test basic cache get/set operations work."""
        # Clear any existing cache first
        cache.clear()
        
        # Test set and get
        cache.set('test_key', 'test_value', 60)
        assert cache.get('test_key') == 'test_value'
        
        # Test delete
        cache.delete('test_key')
        assert cache.get('test_key') is None

    def test_cache_with_timeout(self):
        """Test cache accepts timeout parameter."""
        # Test that timeout parameter is accepted and cache stores the value
        cache.set('timeout_key', 'timeout_value', 3600)
        assert cache.get('timeout_key') == 'timeout_value'
        
        # Clean up
        cache.delete('timeout_key')

    def test_cache_default_value(self):
        """Test cache get with default value."""
        cache.clear()
        default = 'default_value'
        result = cache.get('nonexistent_key', default)
        assert result == default

    def test_cache_add_method(self):
        """Test cache add method (only sets if key doesn't exist)."""
        cache.clear()
        
        # First add should succeed
        assert cache.add('add_key', 'first_value', 60) is True
        assert cache.get('add_key') == 'first_value'
        
        # Second add should fail (key exists)
        assert cache.add('add_key', 'second_value', 60) is False
        assert cache.get('add_key') == 'first_value'

    def test_cache_get_many(self):
        """Test cache get_many method."""
        cache.clear()
        
        cache.set('key1', 'value1', 60)
        cache.set('key2', 'value2', 60)
        cache.set('key3', 'value3', 60)
        
        result = cache.get_many(['key1', 'key2', 'key3', 'nonexistent'])
        assert result == {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}

    def test_cache_set_many(self):
        """Test cache set_many method."""
        cache.clear()
        
        data = {
            'multi_key1': 'multi_value1',
            'multi_key2': 'multi_value2',
            'multi_key3': 'multi_value3',
        }
        cache.set_many(data, 60)
        
        for key, value in data.items():
            assert cache.get(key) == value

    def test_cache_delete_many(self):
        """Test cache delete_many method."""
        cache.clear()
        
        cache.set('del_key1', 'del_value1', 60)
        cache.set('del_key2', 'del_value2', 60)
        cache.set('del_key3', 'del_value3', 60)
        
        cache.delete_many(['del_key1', 'del_key2'])
        
        assert cache.get('del_key1') is None
        assert cache.get('del_key2') is None
        assert cache.get('del_key3') == 'del_value3'

    def test_cache_clear(self):
        """Test cache clear method."""
        cache.set('clear_key1', 'clear_value1', 60)
        cache.set('clear_key2', 'clear_value2', 60)
        
        cache.clear()
        
        assert cache.get('clear_key1') is None
        assert cache.get('clear_key2') is None
