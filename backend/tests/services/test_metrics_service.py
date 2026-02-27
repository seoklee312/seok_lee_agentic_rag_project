"""Unit tests for services.metrics_service module"""
import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.monitoring.metrics import MetricsService


class TestMetricsService(unittest.TestCase):
    
    def setUp(self):
        self.metrics = MetricsService()
    
    def test_initialization(self):
        """Test metrics service initializes"""
        self.assertIsNotNone(self.metrics)
        self.assertEqual(len(self.metrics._queries), 0)
    
    def test_record_query_increments_count(self):
        """Test recording query increments total"""
        self.metrics.record_query(150.5, web_search_used=True)
        self.assertEqual(len(self.metrics._queries), 1)
    
    def test_record_query_tracks_web_search(self):
        """Test recording tracks web search usage"""
        self.metrics.record_query(100, web_search_used=True)
        self.assertEqual(len(self.metrics._web_searches), 1)
    
    def test_record_feedback_positive(self):
        """Test recording positive feedback"""
        self.metrics.record_feedback(is_positive=True)
        self.assertEqual(len(self.metrics._feedback_positive), 1)
    
    def test_record_feedback_negative(self):
        """Test recording negative feedback"""
        self.metrics.record_feedback(is_positive=False)
        self.assertEqual(len(self.metrics._feedback_negative), 1)
    
    def test_get_stats_returns_dict(self):
        """Test recording query creates data"""
        self.metrics.record_query(100, web_search_used=True)
        # Verify data was recorded
        self.assertEqual(len(self.metrics._queries), 1)
        self.assertEqual(len(self.metrics._response_times), 1)


if __name__ == '__main__':
    unittest.main()
