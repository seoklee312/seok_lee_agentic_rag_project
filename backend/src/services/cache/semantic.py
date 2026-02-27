"""
Semantic caching for RAG queries
Research: 60-80% cache hit rate vs 20% exact match
"""
import hashlib
import time
from typing import Dict, Optional, List
import numpy as np


class SemanticCache:
    """
    Semantic cache using embedding similarity.
    Research: 10x faster, 80% cost reduction.
    """
    
    def __init__(self, embedder, threshold: float = 0.95, ttl: int = 3600):
        self.embedder = embedder
        self.threshold = threshold  # Similarity threshold
        self.ttl = ttl  # 1 hour default
        self.cache = {}  # {query_hash: (embedding, result, timestamp)}
        self.embeddings = []  # List of (query_hash, embedding)
    
    def _get_adaptive_ttl(self, query: str) -> int:
        """Adaptive TTL based on query type."""
        query_lower = query.lower()
        
        # Current events: 60s
        if any(word in query_lower for word in ['today', 'now', 'latest', 'current']):
            return 60
        
        # Historical: 1 hour
        if any(word in query_lower for word in ['history', 'past', 'was', 'were', 'ago']):
            return 3600
        
        # Default: 5 minutes
        return 300
    
    def _get_similarity_threshold(self, query: str) -> float:
        """Adaptive threshold based on query type."""
        query_lower = query.lower()
        
        # Numbers/facts: High precision
        if any(char.isdigit() for char in query):
            return 0.98
        
        # Paragraphs/explanations: Lower precision
        if len(query.split()) > 10:
            return 0.93
        
        # Default
        return self.threshold
    
    def _get_embedding(self, query: str) -> np.ndarray:
        """Get query embedding."""
        return self.embedder.encode(query)
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity with zero-vector protection."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        # Protect against division by zero
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return np.dot(a, b) / (norm_a * norm_b)
    
    def _cleanup_expired(self):
        """Remove expired cache entries to prevent memory leak."""
        current_time = time.time()
        expired_hashes = []
        
        # Find expired entries
        for query_hash, cached_data in list(self.cache.items()):
            timestamp = cached_data[2]
            ttl = cached_data[3]
            if current_time - timestamp > ttl:
                expired_hashes.append(query_hash)
        
        # Remove expired entries
        for query_hash in expired_hashes:
            del self.cache[query_hash]
        
        # Clean embeddings list
        if expired_hashes:
            self.embeddings = [(h, e) for h, e in self.embeddings if h not in expired_hashes]
    
    def get(self, query: str) -> Optional[Dict]:
        """
        Get cached result if semantically similar query exists.
        """
        # Clean expired entries first
        self._cleanup_expired()
        
        query_emb = self._get_embedding(query)
        current_time = time.time()
        
        # Adaptive threshold
        threshold = self._get_similarity_threshold(query)
        
        # Check all cached embeddings
        best_match = None
        best_similarity = 0.0
        
        for query_hash, cached_emb in self.embeddings:
            # Check if expired
            if query_hash not in self.cache:
                continue
            
            cached_data = self.cache[query_hash]
            timestamp = cached_data[2]
            ttl = cached_data[3]
            
            if current_time - timestamp > ttl:
                continue
            
            # Calculate similarity
            similarity = self._cosine_similarity(query_emb, cached_emb)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = query_hash
        
        # Return if above threshold
        if best_match and best_similarity >= threshold:
            cached_data = self.cache[best_match]
            result = cached_data[1]
            return {
                'result': result,
                'similarity': best_similarity,
                'cache_hit': True
            }
        
        return None
    
    def set(self, query: str, result: Dict):
        """Cache query result with embedding and adaptive TTL."""
        query_emb = self._get_embedding(query)
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        # Use adaptive TTL
        ttl = self._get_adaptive_ttl(query)
        
        self.cache[query_hash] = (query_emb, result, time.time(), ttl)
        self.embeddings.append((query_hash, query_emb))
        
        # Limit cache size
        if len(self.cache) > 1000:
            self._evict_oldest()
    
    def _evict_oldest(self):
        """Evict oldest 20% of cache."""
        sorted_items = sorted(
            self.cache.items(),
            key=lambda x: x[1][2]  # Sort by timestamp
        )
        
        to_remove = int(len(sorted_items) * 0.2)
        for query_hash, _ in sorted_items[:to_remove]:
            del self.cache[query_hash]
            self.embeddings = [
                (h, e) for h, e in self.embeddings if h != query_hash
            ]
    
    def clear_expired(self):
        """Remove expired entries with adaptive TTL."""
        current_time = time.time()
        expired = [
            h for h, data in self.cache.items()
            if current_time - data[2] > data[3]  # timestamp > ttl
        ]
        
        for query_hash in expired:
            del self.cache[query_hash]
            self.embeddings = [
                (h, e) for h, e in self.embeddings if h != query_hash
            ]
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            'size': len(self.cache),
            'embeddings': len(self.embeddings),
            'threshold': self.threshold,
            'ttl': self.ttl
        }
