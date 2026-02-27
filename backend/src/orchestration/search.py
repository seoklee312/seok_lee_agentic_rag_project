"""Search orchestrator for parallel web + RAG search."""
import asyncio
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """Orchestrates parallel search: xAI Collections → FAISS → Web."""
    
    def __init__(self, web_search_service, rag_engine, cache_service=None, query_optimizer=None, xai_collections=None):
        self.web_search = web_search_service
        self.rag_engine = rag_engine
        self.cache = cache_service
        self.query_optimizer = query_optimizer
        self.xai_collections = xai_collections
        logger.info(f"SearchOrchestrator init: web={type(web_search_service).__name__}, rag={type(rag_engine).__name__}, xai={xai_collections is not None}")
    
    async def parallel_search(
        self, 
        query: str, 
        sub_queries: Optional[List[str]] = None,
        domain: Optional[str] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Execute web and RAG search in parallel.
        
        Args:
            query: Main search query
            sub_queries: Optional sub-queries for multi-query strategy
            domain: Optional domain for xAI Collections routing
            
        Returns:
            Tuple of (web_results, rag_results)
        """
        logger.info("⚡ Starting parallel search (web + RAG)...")
        
        # Create tasks
        web_task = asyncio.create_task(self._search_web(query))
        rag_task = asyncio.create_task(self._search_rag(query, sub_queries, domain))
        
        # Execute in parallel
        web_results, rag_results = await asyncio.gather(web_task, rag_task)
        
        return web_results, rag_results
    
    async def _search_web(self, query: str) -> List[Dict]:
        """Search web with caching and query expansion."""
        import time
        start = time.time()
        
        # Check if using WebSearchAgent (has .search method that returns dict)
        is_web_agent = hasattr(self.web_search, 'search') and hasattr(self.web_search, 'llm')
        
        # Expand query if optimizer available and NOT using WebSearchAgent (it does its own expansion)
        web_queries = [query]
        if self.query_optimizer and not is_web_agent:
            try:
                understanding = await self.query_optimizer.understand_query(query)
                if understanding and understanding.get('web_queries'):
                    web_queries = understanding['web_queries'][:2]  # Limit to 2
                    logger.info(f"🔍 Web Query Expansion: {len(web_queries)} queries")
                    for i, wq in enumerate(web_queries, 1):
                        logger.info(f"  {i}. '{wq}'")
            except Exception as e:
                logger.warning(f"Query expansion failed: {e}")
        
        # Check cache
        if self.cache and hasattr(self.cache, 'enabled') and self.cache.enabled:
            cached = self.cache.get_web_results(query)
            if cached:
                elapsed = (time.time() - start) * 1000
                logger.info(f"🎯 Web cache hit in {elapsed:.0f}ms")
                return cached
        
        # Execute search based on type
        if is_web_agent:
            # WebSearchAgent - advanced search with built-in expansion
            try:
                understanding = self.query_optimizer.understand_query(query) if self.query_optimizer else {}
                intent = understanding.get('intent', 'question')
                web_queries_for_agent = understanding.get('web_queries', [query])
                
                result = await self.web_search.search(query, intent, web_queries_for_agent)
                unique_results = result.get('results', [])
                elapsed = (time.time() - start) * 1000
                logger.info(f"🌐 WebSearchAgent: {len(unique_results)} results in {elapsed:.0f}ms (strategy: {result.get('strategy')})")
            except Exception as e:
                logger.warning(f"⚠️ WebSearchAgent failed: {e}")
                unique_results = []
        else:
            # WebSearchService - basic search with manual expansion
            all_results = []
            for i, wq in enumerate(web_queries, 1):
                try:
                    results = self.web_search.search(wq, num_results=5)
                    logger.info(f"🌐 Query {i} '{wq[:50]}...': {len(results)} results")
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"⚠️ Web search failed for query {i}: {e}")
            
            # Deduplicate by URL
            seen_urls = set()
            unique_results = []
            for r in all_results:
                url = r.get('url')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(r)
            
            elapsed = (time.time() - start) * 1000
            logger.info(f"🌐 Web search: {len(unique_results)} unique results in {elapsed:.0f}ms")
        
        # Cache results
        if self.cache and hasattr(self.cache, 'enabled') and self.cache.enabled and unique_results:
            self.cache.set_web_results(query, unique_results, ttl=300)
        
        return unique_results
    
    async def _search_rag(self, query: str, sub_queries: Optional[List[str]] = None, domain: Optional[str] = None) -> List[Dict]:
        """Search RAG: xAI Collections → FAISS backup."""
        import time
        start = time.time()
        
        # Check cache
        if self.cache and hasattr(self.cache, 'enabled') and self.cache.enabled:
            cached = self.cache.get_rag_results(query)
            if cached:
                elapsed = (time.time() - start) * 1000
                logger.info(f"🎯 RAG cache hit: {len(cached)} docs in {elapsed:.0f}ms")
                return cached
        
        results = []
        
        # Try xAI Collections first (if domain provided)
        logger.info(f"🔍 xAI Collections check: client={self.xai_collections is not None}, domain={domain}")
        if self.xai_collections and domain:
            try:
                collection_id = self._get_collection_id(domain)
                logger.info(f"🔍 Collection ID for domain '{domain}': {collection_id}")
                if collection_id:
                    results = await self.xai_collections.query(
                        query_text=query,
                        collection_name=collection_id,
                        top_k=5
                    )
                    if results and len(results) > 0:
                        elapsed = (time.time() - start) * 1000
                        logger.info(f"✅ xAI Collections: {len(results)} docs in {elapsed:.0f}ms")
                        
                        # Cache and return
                        if self.cache and hasattr(self.cache, 'enabled') and self.cache.enabled:
                            self.cache.set_rag_results(query, results, ttl=3600)
                        return results
            except Exception as e:
                logger.warning(f"xAI Collections failed: {e}, falling back to FAISS")
        
        # Fallback to FAISS
        if sub_queries and len(sub_queries) > 1:
            # Multi-query strategy
            all_results = []
            for sq in sub_queries[:2]:
                sq_results = self.rag_engine.search(sq)
                all_results.extend(sq_results)
                logger.info(f"📚 FAISS sub-query '{sq[:40]}...': {len(sq_results)} docs")
            
            # Deduplicate
            seen = set()
            unique_results = []
            for doc in all_results:
                doc_id = doc.get('metadata', {}).get('doc_id')
                if doc_id and doc_id not in seen:
                    seen.add(doc_id)
                    unique_results.append(doc)
            results = unique_results[:5]
        else:
            # Single query
            results = self.rag_engine.search(query)
        
        # Cache results
        if self.cache and hasattr(self.cache, 'enabled') and self.cache.enabled and results:
            self.cache.set_rag_results(query, results, ttl=3600)
        
        elapsed = (time.time() - start) * 1000
        logger.info(f"📚 FAISS backup: {len(results)} docs in {elapsed:.0f}ms")
        
        return results
    
    def _get_collection_id(self, domain: str) -> Optional[str]:
        """Get xAI collection ID for domain from config."""
        if not domain or not self.xai_collections:
            return None
        
        # Read from config.yaml via xAI Collections client
        if hasattr(self.xai_collections, 'config'):
            collections = self.xai_collections.config.get('collections', {})
            return collections.get(domain)
        
        return None
    

