"""Unit tests for services.vector_search module"""
import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.faiss.vector import VectorSearchService
from sentence_transformers import SentenceTransformer


class TestVectorSearchService(unittest.TestCase):
    
    def setUp(self):
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.service = VectorSearchService(self.model)
    
    def test_build_index(self):
        texts = ['machine learning', 'deep learning']
        self.service.build_index(texts)
        self.assertEqual(self.service.index.ntotal, 2)
    
    def test_search_empty_index(self):
        """Test search on empty index returns empty list"""
        result = self.service.search("query", top_k=5)
        self.assertEqual(result, [])
    
    def test_add_vectors(self):
        """Test adding vectors to existing index"""
        import faiss
        self.service.dimension = 384
        self.service.index = faiss.IndexFlatL2(384)
        
        self.service.add_vectors(["test text", "another text"])
        self.assertEqual(self.service.index.ntotal, 2)


if __name__ == '__main__':
    unittest.main()
