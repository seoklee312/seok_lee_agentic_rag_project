"""Unit tests for core.chunking module"""
import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.faiss.core.chunking import FixedChunker, SemanticChunker
from sentence_transformers import SentenceTransformer


class TestFixedChunker(unittest.TestCase):
    
    def test_basic_chunking(self):
        chunker = FixedChunker(chunk_size=5, chunk_overlap=2)
        text = "one two three four five six seven eight nine ten"
        chunks = chunker.chunk(text)
        self.assertGreater(len(chunks), 1)
    
    def test_empty_text(self):
        chunker = FixedChunker(chunk_size=5, chunk_overlap=2)
        self.assertEqual(chunker.chunk(""), [])
        self.assertEqual(chunker.chunk("   "), [])
    
    def test_overlap_validation(self):
        with self.assertRaises(ValueError):
            FixedChunker(chunk_size=5, chunk_overlap=5)


class TestSemanticChunker(unittest.TestCase):
    
    def setUp(self):
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    def test_empty_text(self):
        chunker = SemanticChunker(self.model)
        self.assertEqual(chunker.chunk(""), [])
        self.assertEqual(chunker.chunk("   "), [])
    
    def test_single_sentence(self):
        chunker = SemanticChunker(self.model)
        result = chunker.chunk("This is a test.")
        self.assertEqual(len(result), 1)


if __name__ == '__main__':
    unittest.main()
