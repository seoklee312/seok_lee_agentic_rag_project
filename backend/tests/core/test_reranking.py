"""Unit tests for core.reranking module"""
import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.faiss.core.reranking import CrossEncoderReranker, BM25Reranker, HybridReranker
from sentence_transformers import SentenceTransformer


class TestCrossEncoderReranker(unittest.TestCase):
    
    def setUp(self):
        self.reranker = CrossEncoderReranker('cross-encoder/ms-marco-TinyBERT-L-2-v2')
    
    def test_empty_results(self):
        result = self.reranker.rerank("query", [], 3)
        self.assertEqual(result, [])
    
    def test_identical_scores(self):
        """Test handling of identical scores"""
        results = [
            {'text': 'same text', 'score': 0.5},
            {'text': 'same text', 'score': 0.5}
        ]
        reranked = self.reranker.rerank("query", results, 2)
        self.assertEqual(len(reranked), 2)
        for doc in reranked:
            self.assertIn('rerank_score', doc)


class TestBM25Reranker(unittest.TestCase):
    
    def test_basic_reranking(self):
        documents = [
            {'text': 'machine learning', 'metadata': {}},
            {'text': 'deep learning', 'metadata': {}}
        ]
        reranker = BM25Reranker(documents)
        results = documents.copy()
        reranked = reranker.rerank("learning", results, 2)
        self.assertEqual(len(reranked), 2)


class TestHybridReranker(unittest.TestCase):
    
    def test_identical_bm25_scores(self):
        """Test handling of identical BM25 scores"""
        documents = [
            {'text': 'test', 'metadata': {}},
            {'text': 'test', 'metadata': {}}
        ]
        reranker = HybridReranker('cross-encoder/ms-marco-TinyBERT-L-2-v2', documents)
        reranked = reranker.rerank("query", documents.copy(), 2)
        self.assertEqual(len(reranked), 2)


if __name__ == '__main__':
    unittest.main()
