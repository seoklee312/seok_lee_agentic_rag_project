"""Unit tests for services.document_manager module"""
import unittest
import sys
import os
import tempfile
import threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.faiss.manager import DocumentManager


class TestDocumentManager(unittest.TestCase):
    
    def setUp(self):
        self.temp_file = tempfile.mktemp()
        self.manager = DocumentManager(storage_path=self.temp_file)
    
    def test_add_document(self):
        doc = self.manager.add_document("Test content", {"key": "value"})
        self.assertIn('id', doc)
        self.assertEqual(doc['content'], "Test content")
    
    def test_custom_id(self):
        doc = self.manager.add_document("Content", custom_id="custom-123")
        self.assertEqual(doc['id'], "custom-123")
    
    def test_duplicate_custom_id(self):
        self.manager.add_document("Content 1", custom_id="dup-id")
        with self.assertRaises(ValueError):
            self.manager.add_document("Content 2", custom_id="dup-id")
    
    def test_duplicate_content(self):
        self.manager.add_document("Same content")
        with self.assertRaises(ValueError):
            self.manager.add_document("Same content")
    
    def test_document_limit(self):
        """Test 10K document limit"""
        self.manager.documents = {str(i): {} for i in range(10000)}
        with self.assertRaises(ValueError):
            self.manager.add_document("Over limit")
    
    def test_thread_safety(self):
        """Test concurrent additions"""
        errors = []
        
        def add_doc(i):
            try:
                self.manager.add_document(f"Content {i}", {"index": i})
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=add_doc, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(self.manager.documents), 10)


if __name__ == '__main__':
    unittest.main()
