"""
Tests for credentials caching functionality.
"""
from django.test import TestCase
from django.core.cache import cache
from givefood.const.general import CRED_MC_KEY_PREFIX


class TestCredentialsCaching(TestCase):
    """Test credentials caching functionality."""

    def setUp(self):
        """Setup test data before each test."""
        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        """Cleanup after each test."""
        cache.clear()

    def test_cache_key_format(self):
        """Test that the cache key format is correct."""
        # Verify the cache key prefix is set
        self.assertEqual(CRED_MC_KEY_PREFIX, "cred_")
        
        # Test cache key format
        test_cred_name = "test_api_key"
        expected_cache_key = f"{CRED_MC_KEY_PREFIX}{test_cred_name}"
        self.assertEqual(expected_cache_key, "cred_test_api_key")

    def test_cache_set_and_get(self):
        """Test that we can set and get values from cache using our key format."""
        test_cred_name = "test_key"
        test_value = "test_value"
        cache_key = f"{CRED_MC_KEY_PREFIX}{test_cred_name}"
        
        # Set value in cache
        cache.set(cache_key, test_value, 3600)
        
        # Get value from cache
        cached_value = cache.get(cache_key)
        self.assertEqual(cached_value, test_value)

    def test_cache_delete(self):
        """Test that we can delete values from cache."""
        test_cred_name = "test_key"
        test_value = "test_value"
        cache_key = f"{CRED_MC_KEY_PREFIX}{test_cred_name}"
        
        # Set value in cache
        cache.set(cache_key, test_value, 3600)
        self.assertEqual(cache.get(cache_key), test_value)
        
        # Delete value from cache
        cache.delete(cache_key)
        self.assertIsNone(cache.get(cache_key))

    def test_multiple_credentials_cache(self):
        """Test that we can cache multiple credentials independently."""
        # Set multiple credentials in cache
        cache.set(f"{CRED_MC_KEY_PREFIX}key1", "value1", 3600)
        cache.set(f"{CRED_MC_KEY_PREFIX}key2", "value2", 3600)
        cache.set(f"{CRED_MC_KEY_PREFIX}key3", "value3", 3600)
        
        # Verify all are cached
        self.assertEqual(cache.get(f"{CRED_MC_KEY_PREFIX}key1"), "value1")
        self.assertEqual(cache.get(f"{CRED_MC_KEY_PREFIX}key2"), "value2")
        self.assertEqual(cache.get(f"{CRED_MC_KEY_PREFIX}key3"), "value3")
        
        # Delete one
        cache.delete(f"{CRED_MC_KEY_PREFIX}key2")
        
        # Verify only the deleted one is gone
        self.assertEqual(cache.get(f"{CRED_MC_KEY_PREFIX}key1"), "value1")
        self.assertIsNone(cache.get(f"{CRED_MC_KEY_PREFIX}key2"))
        self.assertEqual(cache.get(f"{CRED_MC_KEY_PREFIX}key3"), "value3")
