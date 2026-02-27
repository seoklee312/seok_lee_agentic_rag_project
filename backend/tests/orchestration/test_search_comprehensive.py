"""Comprehensive tests for orchestration.search module"""
import unittest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from orchestration.search import SearchOrchestrator  # Direct import to avoid circular dependency


class TestSearchOrchestrator(unittest.TestCase):
    """Test SearchOrchestrator parallel search coordination"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_web_search = Mock()
        self.mock_rag_engine = Mock()
        self.mock_cache = Mock()
        self.mock_cache.enabled = True
        
        self.orchestrator = SearchOrchestrator(
            self.mock_web_search,
            self.mock_rag_engine,
            self.mock_cache
        )
    
    def test_initialization(self):
        """Test orchestrator initialization"""
        self.assertIsNotNone(self.orchestrator)
        self.assertEqual(self.orchestrator.web_search, self.mock_web_search)
        self.assertEqual(self.orchestrator.rag_engine, self.mock_rag_engine)
        self.assertEqual(self.orchestrator.cache, self.mock_cache)
    
    def test_parallel_search_both_sources(self):
        """Test parallel search executes both web and RAG"""
        # Setup mocks
        self.mock_web_search.search.return_value = [{'title': 'Web result'}]
        self.mock_rag_engine.search.return_value = [{'text': 'RAG result'}]
        self.mock_cache.get_web_results.return_value = None
        self.mock_cache.get_rag_results.return_value = None
        
        # Run async test
        async def run_test():
            web_results, rag_results = await self.orchestrator.parallel_search("test query")
            self.assertEqual(len(web_results), 1)
            self.assertEqual(len(rag_results), 1)
            self.mock_web_search.search.assert_called_once()
            self.mock_rag_engine.search.assert_called_once()
        
        asyncio.run(run_test())
    
    def test_web_search_with_cache_hit(self):
        """Test web search returns cached results"""
        cached_results = [{'title': 'Cached'}]
        self.mock_cache.get_web_results.return_value = cached_results
        
        async def run_test():
            results = await self.orchestrator._search_web("test")
            self.assertEqual(results, cached_results)
            self.mock_web_search.search.assert_not_called()
        
        asyncio.run(run_test())
    
    def test_web_search_cache_miss(self):
        """Test web search fetches and caches on miss"""
        self.mock_cache.get_web_results.return_value = None
        self.mock_web_search.search.return_value = [{'title': 'Fresh'}]
        
        async def run_test():
            results = await self.orchestrator._search_web("test")
            self.assertEqual(len(results), 1)
            self.mock_web_search.search.assert_called_once()
            self.mock_cache.set_web_results.assert_called_once()
        
        asyncio.run(run_test())
    
    def test_rag_search_with_cache_hit(self):
        """Test RAG search returns cached results"""
        cached_results = [{'text': 'Cached RAG'}]
        self.mock_cache.get_rag_results.return_value = cached_results
        
        async def run_test():
            results = await self.orchestrator._search_rag("test")
            self.assertEqual(results, cached_results)
            self.mock_rag_engine.search.assert_not_called()
        
        asyncio.run(run_test())
    
    def test_rag_search_multi_query(self):
        """Test RAG search with multiple sub-queries"""
        self.mock_cache.get_rag_results.return_value = None
        self.mock_rag_engine.search.return_value = [
            {'text': 'Result 1', 'metadata': {'doc_id': '1'}},
            {'text': 'Result 2', 'metadata': {'doc_id': '2'}}
        ]
        
        async def run_test():
            results = await self.orchestrator._search_rag("test", ["query1", "query2"])
            self.assertIsInstance(results, list)
            # Should deduplicate by doc_id
            self.mock_rag_engine.search.assert_called()
        
        asyncio.run(run_test())
    
    def test_web_search_error_handling(self):
        """Test web search handles errors gracefully"""
        self.mock_cache.get_web_results.return_value = None
        self.mock_web_search.search.side_effect = Exception("Network error")
        
        async def run_test():
            results = await self.orchestrator._search_web("test")
            self.assertEqual(results, [])  # Should return empty on error
        
        asyncio.run(run_test())
    
    def test_cache_disabled(self):
        """Test orchestrator works without cache"""
        orchestrator = SearchOrchestrator(self.mock_web_search, self.mock_rag_engine, None)
        self.mock_web_search.search.return_value = [{'title': 'Result'}]
        self.mock_rag_engine.search.return_value = [{'text': 'Doc'}]
        
        async def run_test():
            web_results, rag_results = await orchestrator.parallel_search("test")
            self.assertIsNotNone(web_results)
            self.assertIsNotNone(rag_results)
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
