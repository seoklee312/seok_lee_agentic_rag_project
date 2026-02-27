"""Unit tests for services.query_optimizer module"""
import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.query.optimizer import QueryOptimizer


class TestQueryOptimizer(unittest.TestCase):
    
    def setUp(self):
        self.optimizer = QueryOptimizer()
    
    def test_initialization(self):
        """Test optimizer initializes"""
        self.assertIsNotNone(self.optimizer)
    
    def test_understand_query_greeting(self):
        """Test greeting detection with LLM service"""
        from unittest.mock import Mock
        optimizer = QueryOptimizer(llm_service=Mock())
        result = optimizer.understand_query("hi")
        self.assertTrue(result['is_greeting'])
        self.assertFalse(result['needs_web'])
    
    def test_understand_query_current_events(self):
        """Test current events detection"""
        result = self.optimizer.understand_query("latest Lakers news")
        self.assertTrue(result['needs_web'])
    
    def test_understand_query_returns_dict(self):
        """Test understand_query returns dict"""
        result = self.optimizer.understand_query("Lakers score")
        self.assertIsInstance(result, dict)
        self.assertIn('needs_web', result)
        self.assertIn('web_query', result)
    
    def test_expand_abbreviations(self):
        """Test abbreviation expansion"""
        expanded = self.optimizer.expand_abbreviations("NBA game")
        self.assertIsInstance(expanded, str)
    
    def test_understand_query_without_llm(self):
        """Test query understanding without LLM service"""
        optimizer = QueryOptimizer(llm_service=None)
        result = optimizer.understand_query("Lakers score")
        self.assertIsInstance(result, dict)
        self.assertTrue(result['needs_web'])


if __name__ == '__main__':
    unittest.main()
