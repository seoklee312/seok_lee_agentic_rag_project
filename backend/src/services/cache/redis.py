"""Redis caching service for embeddings, web results, and RAG results."""
import json
import pickle
import hashlib
import logging
from typing import Optional, List, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - caching disabled")


class CacheService:
    """Multi-level caching with Redis."""
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        host = config.get('host', 'localhost')
        port = config.get('port', 6379)
        db = config.get('db', 0)
        socket_timeout = config.get('socket_timeout', 2)
        
        self.enabled = REDIS_AVAILABLE
        self.client = None
        
        if self.enabled:
            try:
                self.client = redis.Redis(
                    host=host, 
                    port=port, 
                    db=db,
                    decode_responses=False,
                    socket_connect_timeout=socket_timeout
                )
                self.client.ping()
                logger.info("✅ Redis cache connected")
            except Exception as e:
                logger.warning(f"⚠️ Redis unavailable: {e} - caching disabled")
                self.enabled = False
    
    def _hash_key(self, prefix: str, data: str) -> str:
        """Generate cache key."""
        hash_val = hashlib.md5(data.encode()).hexdigest()
        return f"{prefix}:{hash_val}"
    
    # Embedding cache (permanent)
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get cached embedding."""
        if not self.enabled:
            return None
        
        try:
            key = self._hash_key("embed", text)
            cached = self.client.get(key)
            if cached:
                logger.debug(f"🎯 Embedding cache hit")
                return pickle.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        
        return None
    
    def set_embedding(self, text: str, embedding: np.ndarray):
        """Cache embedding (no expiry)."""
        if not self.enabled:
            return
        
        try:
            key = self._hash_key("embed", text)
            self.client.set(key, pickle.dumps(embedding))
            logger.debug(f"💾 Embedding cached")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    # Web search cache (5 min TTL)
    def get_web_results(self, query: str) -> Optional[List[Dict]]:
        """Get cached web results."""
        if not self.enabled:
            return None
        
        try:
            key = self._hash_key("web", query)
            cached = self.client.get(key)
            if cached:
                logger.info(f"🎯 Web cache hit: '{query[:50]}...'")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        
        return None
    
    def set_web_results(self, query: str, results: List[Dict], ttl: int = 300):
        """Cache web results (5 min default)."""
        if not self.enabled:
            return
        
        try:
            key = self._hash_key("web", query)
            self.client.setex(key, ttl, json.dumps(results))
            logger.debug(f"💾 Web results cached (TTL={ttl}s)")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    # RAG results cache (1 hour TTL)
    def get_rag_results(self, query: str) -> Optional[List[Dict]]:
        """Get cached RAG results."""
        if not self.enabled:
            return None
        
        try:
            key = self._hash_key("rag", query)
            cached = self.client.get(key)
            if cached:
                logger.info(f"🎯 RAG cache hit: '{query[:50]}...'")
                return pickle.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        
        return None
    
    def set_rag_results(self, query: str, results: List[Dict], ttl: int = 3600):
        """Cache RAG results (1 hour default)."""
        if not self.enabled:
            return
        
        try:
            key = self._hash_key("rag", query)
            self.client.setex(key, ttl, pickle.dumps(results))
            logger.debug(f"💾 RAG results cached (TTL={ttl}s)")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    # Semantic cache (similar queries)
    def get_semantic_cache(self, query_embedding: np.ndarray, threshold: float = 0.95) -> Optional[Any]:
        """Get cached result for similar query."""
        if not self.enabled:
            return None
        
        try:
            # Get all semantic cache keys
            keys = self.client.keys("semantic:*")
            
            for key in keys[:100]:  # Limit search
                cached = self.client.get(key)
                if cached:
                    data = pickle.loads(cached)
                    cached_embedding = data['embedding']
                    
                    # Cosine similarity
                    similarity = np.dot(query_embedding, cached_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(cached_embedding)
                    )
                    
                    if similarity >= threshold:
                        logger.info(f"🎯 Semantic cache hit (similarity={similarity:.3f})")
                        return data['result']
        except Exception as e:
            logger.warning(f"Semantic cache error: {e}")
        
        return None
    
    def set_semantic_cache(self, query: str, query_embedding: np.ndarray, result: Any, ttl: int = 3600):
        """Cache result with query embedding for semantic matching."""
        if not self.enabled:
            return
        
        try:
            key = self._hash_key("semantic", query)
            data = {
                'embedding': query_embedding,
                'result': result,
                'query': query
            }
            self.client.setex(key, ttl, pickle.dumps(data))
            logger.debug(f"💾 Semantic cache stored")
        except Exception as e:
            logger.warning(f"Semantic cache set error: {e}")
    
    def clear_all(self):
        """Clear all cache (use with caution)."""
        if not self.enabled:
            return
        
        try:
            self.client.flushdb()
            logger.info("🗑️ Cache cleared")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")


# Global instance - will be initialized with config in app.py
cache_service = None
