"""Unit tests for services.cache_service module"""
import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.cache.service import CacheService
from unittest.mock import Mock, patch
import numpy as np


class TestCacheService(unittest.TestCase):
    
    def setUp(self):
        """Set up cache service with mocked Redis"""
        with patch('services.cache_service.REDIS_AVAILABLE', False):
            self.cache = CacheService()
    
    def test_initialization_without_redis(self):
        """Test cache initializes without Redis"""
        with patch('services.cache_service.REDIS_AVAILABLE', False):
            cache = CacheService()
            self.assertFalse(cache.enabled)
    
    def test_get_embedding_disabled_returns_none(self):
        """Test get_embedding returns None when disabled"""
        result = self.cache.get_embedding('test text')
        self.assertIsNone(result)
    
    def test_set_embedding_when_disabled_no_error(self):
        """Test set_embedding doesn't error when disabled"""
        try:
            embedding = np.array([0.1, 0.2, 0.3])
            self.cache.set_embedding('test text', embedding)
        except Exception as e:
            self.fail(f"set_embedding raised exception: {e}")
    
    def test_get_web_results_disabled_returns_none(self):
        """Test get_web_results returns None when disabled"""
        result = self.cache.get_web_results('test query')
        self.assertIsNone(result)
    
    def test_set_web_results_when_disabled_no_error(self):
        """Test set_web_results doesn't error when disabled"""
        try:
            results = [{'title': 'Test', 'url': 'http://example.com'}]
            self.cache.set_web_results('test query', results)
        except Exception as e:
            self.fail(f"set_web_results raised exception: {e}")


if __name__ == '__main__':
    unittest.main()
