"""Comprehensive tests for services.cache module"""
import unittest
from unittest.mock import Mock, patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.cache.service import CacheService


class TestCacheService(unittest.TestCase):
    """Test CacheService semantic caching"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.service = CacheService(enabled=True, ttl=3600)
    
    def test_initialization_enabled(self):
        """Test service initialization with cache enabled"""
        service = CacheService(enabled=True)
        self.assertTrue(service.enabled)
    
    def test_initialization_disabled(self):
        """Test service initialization with cache disabled"""
        service = CacheService(enabled=False)
        self.assertFalse(service.enabled)
    
    def test_set_and_get(self):
        """Test setting and getting cache values"""
        self.service.set("test_key", "test_value")
        value = self.service.get("test_key")
        self.assertEqual(value, "test_value")
    
    def test_get_nonexistent_key(self):
        """Test getting non-existent key returns None"""
        value = self.service.get("nonexistent")
        self.assertIsNone(value)
    
    def test_delete_key(self):
        """Test deleting a key"""
        self.service.set("test_key", "test_value")
        self.service.delete("test_key")
        value = self.service.get("test_key")
        self.assertIsNone(value)
    
    def test_clear_cache(self):
        """Test clearing entire cache"""
        self.service.set("key1", "value1")
        self.service.set("key2", "value2")
        self.service.clear()
        self.assertIsNone(self.service.get("key1"))
        self.assertIsNone(self.service.get("key2"))
    
    def test_cache_disabled_operations(self):
        """Test operations when cache is disabled"""
        service = CacheService(enabled=False)
        service.set("key", "value")
        value = service.get("key")
        self.assertIsNone(value)  # Should not cache when disabled
    
    def test_ttl_expiration(self):
        """Test TTL expiration"""
        import time
        service = CacheService(enabled=True, ttl=1)  # 1 second TTL
        service.set("key", "value")
        time.sleep(2)
        value = service.get("key")
        self.assertIsNone(value)  # Should be expired
    
    def test_semantic_similarity(self):
        """Test semantic similarity for query matching"""
        self.service.set("what is python", "Python is a programming language")
        # Similar query should hit cache
        value = self.service.get("what is python programming")
        self.assertIsNotNone(value)
    
    def test_cache_hit_count(self):
        """Test cache hit counting"""
        self.service.set("key", "value")
        self.service.get("key")
        self.service.get("key")
        stats = self.service.get_stats()
        self.assertGreater(stats['hits'], 0)
    
    def test_cache_miss_count(self):
        """Test cache miss counting"""
        self.service.get("nonexistent")
        stats = self.service.get_stats()
        self.assertGreater(stats['misses'], 0)
    
    def test_cache_size(self):
        """Test cache size tracking"""
        self.service.set("key1", "value1")
        self.service.set("key2", "value2")
        stats = self.service.get_stats()
        self.assertEqual(stats['size'], 2)
    
    def test_eviction_policy(self):
        """Test cache eviction when full"""
        service = CacheService(enabled=True, max_size=2)
        service.set("key1", "value1")
        service.set("key2", "value2")
        service.set("key3", "value3")  # Should evict oldest
        self.assertIsNone(service.get("key1"))
        self.assertIsNotNone(service.get("key3"))


if __name__ == '__main__':
    unittest.main()
