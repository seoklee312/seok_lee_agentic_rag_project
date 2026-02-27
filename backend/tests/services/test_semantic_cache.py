"""Unit tests for services.semantic_cache module"""
import unittest
import sys
import os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.cache.semantic import SemanticCache
from unittest.mock import Mock


class TestSemanticCache(unittest.TestCase):
    
    def setUp(self):
        self.embedder = Mock()
        self.embedder.embed = Mock(return_value=np.array([0.1, 0.2, 0.3]))
        self.cache = SemanticCache(self.embedder, threshold=0.95, ttl=3600)
    
    def test_initialization(self):
        """Test cache initializes with correct config"""
        self.assertEqual(self.cache.threshold, 0.95)
        self.assertEqual(self.cache.ttl, 3600)
        self.assertEqual(len(self.cache.cache), 0)
    
    def test_get_adaptive_ttl_current_events(self):
        """Test adaptive TTL for current events"""
        ttl = self.cache._get_adaptive_ttl('Lakers game today')
        self.assertEqual(ttl, 60)
    
    def test_get_adaptive_ttl_historical(self):
        """Test adaptive TTL for historical queries"""
        ttl = self.cache._get_adaptive_ttl('Lakers history')
        self.assertEqual(ttl, 3600)
    
    def test_get_adaptive_ttl_default(self):
        """Test adaptive TTL for general queries"""
        ttl = self.cache._get_adaptive_ttl('Lakers information')
        self.assertEqual(ttl, 300)
    
    def test_get_similarity_threshold_numbers(self):
        """Test adaptive threshold for number queries"""
        threshold = self.cache._get_similarity_threshold('Lakers score 118')
        self.assertEqual(threshold, 0.98)
    
    def test_get_similarity_threshold_long(self):
        """Test adaptive threshold for long queries"""
        query = 'Explain the Lakers vs Celtics game strategy and key plays today'  # 11 words
        threshold = self.cache._get_similarity_threshold(query)
        self.assertEqual(threshold, 0.93)  # >10 words = 0.93
    
    def test_get_similarity_threshold_default(self):
        """Test adaptive threshold for normal queries"""
        threshold = self.cache._get_similarity_threshold('Lakers game')
        self.assertEqual(threshold, 0.95)
    
    def test_set_and_get_cache_hit(self):
        """Test cache set and get with hit"""
        query = 'test query'
        result = {'answer': 'test answer'}
        
        self.cache.set(query, result)
        cached = self.cache.get(query)
        
        self.assertIsNotNone(cached)
        self.assertTrue(cached['cache_hit'])
        self.assertEqual(cached['result'], result)
    
    def test_get_cache_miss(self):
        """Test cache get with miss"""
        cached = self.cache.get('nonexistent query')
        self.assertIsNone(cached)
    
    def test_cache_size_limit(self):
        """Test cache evicts oldest entries when full"""
        # Fill cache beyond limit
        for i in range(1100):
            self.cache.set(f'query_{i}', {'answer': f'answer_{i}'})
        
        # Should evict oldest 20%
        self.assertLessEqual(len(self.cache.cache), 1000)


if __name__ == '__main__':
    unittest.main()
