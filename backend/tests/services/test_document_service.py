"""Unit tests for document ingestion service"""
import pytest
import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from services.faiss.ingestion import DocumentIngestionService

class MockChunker:
    def chunk(self, text):
        # Simple mock: split by sentences
        return [s.strip() + '.' for s in text.split('.') if s.strip()]

class TestDocumentIngestionService:
    @pytest.fixture
    def service(self):
        chunker = MockChunker()
        return DocumentIngestionService(chunker)
    
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            with open(os.path.join(tmpdir, "doc1.txt"), "w") as f:
                f.write("This is test document 1. " * 10)
            with open(os.path.join(tmpdir, "doc2.txt"), "w") as f:
                f.write("This is test document 2. " * 10)
            yield tmpdir
    
    def test_ingest_from_directory(self, service, temp_dir):
        docs = service.ingest_from_directory(temp_dir)
        assert len(docs) > 0
        assert all('text' in doc for doc in docs)
        assert all('source' in doc for doc in docs)
    
    def test_invalid_directory(self, service):
        with pytest.raises(ValueError, match="Directory not found"):
            service.ingest_from_directory("/nonexistent")
    
    def test_empty_directory(self, service):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="No .txt files found"):
                service.ingest_from_directory(tmpdir)
