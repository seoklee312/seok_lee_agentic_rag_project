"""Unit tests for services.feedback_collector module"""
import unittest
import sys
import os
import tempfile
import threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.feedback.collector import FeedbackCollector


class TestFeedbackCollector(unittest.TestCase):
    
    def setUp(self):
        self.temp_file = tempfile.mktemp()
        self.collector = FeedbackCollector(storage_path=self.temp_file)
    
    def test_add_feedback(self):
        feedback = self.collector.add_feedback("Test query", 1, "Good")
        self.assertIn('id', feedback)
        self.assertEqual(feedback['rating'], 1)
    
    def test_invalid_rating(self):
        with self.assertRaises(ValueError):
            self.collector.add_feedback("Query", 5)
    
    def test_get_stats(self):
        self.collector.add_feedback("Q1", 1)
        self.collector.add_feedback("Q2", -1)
        stats = self.collector.get_feedback_stats()
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['positive'], 1)
        self.assertEqual(stats['negative'], 1)
    
    def test_thread_safety(self):
        """Test concurrent feedback submissions"""
        errors = []
        
        def add_feedback(i):
            try:
                self.collector.add_feedback(f"Query {i}", 1 if i % 2 == 0 else -1)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=add_feedback, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(self.collector.feedback), 10)


if __name__ == '__main__':
    unittest.main()
