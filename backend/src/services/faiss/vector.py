"""
Vector search service using FAISS
Manages FAISS index operations only - document storage handled by DocumentManager
"""
import faiss
import numpy as np
import logging
import os
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class VectorSearchService:
    """FAISS-based vector search - index operations only"""
    
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        self.index = None
        self.dimension = None
    
    def build_index(self, texts: List[str]):
        """Build FAISS index from text list"""
        if not texts:
            raise ValueError("No texts provided for indexing")
        
        logger.info(f"Encoding {len(texts)} texts...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        
        self.dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings.astype('float32'))
        
        logger.info(f"FAISS index built with {self.index.ntotal} vectors")
    
    def search(self, query: str, top_k: int = 5, distance_threshold: float = None) -> List[Tuple[int, float]]:
        """Search and return (index, score) tuples"""
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Index is empty, returning no results")
            return []
        
        actual_k = min(top_k, self.index.ntotal)
        
        query_embedding = self.embedding_model.encode([query])
        distances, indices = self.index.search(query_embedding.astype('float32'), actual_k)
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if distance_threshold and distance > distance_threshold:
                logger.debug(f"Filtered result with distance {distance:.3f} > threshold {distance_threshold}")
                continue
            results.append((int(idx), float(distance)))
        
        return results
    
    def add_vectors(self, texts: List[str]):
        """Add vectors for new texts to existing index"""
        if self.index is None:
            raise ValueError("Index not initialized")
        
        if self.dimension is None:
            self.dimension = self.embedding_model.get_sentence_embedding_dimension()
        
        embeddings = self.embedding_model.encode(texts)
        self.index.add(embeddings.astype('float32'))
        
        logger.info(f"Added {len(texts)} vectors to index (total: {self.index.ntotal})")
    
    def save_index(self, index_path: str):
        """Save FAISS index to disk"""
        if self.index is None:
            logger.warning("No index to save")
            return
        
        os.makedirs(os.path.dirname(index_path) or '.', exist_ok=True)
        faiss.write_index(self.index, index_path)
        
        logger.info(f"Index saved to {index_path}")
    
    def load_index(self, index_path: str) -> bool:
        """Load FAISS index from disk"""
        if not os.path.exists(index_path):
            logger.info("No saved index found")
            return False
        
        try:
            self.index = faiss.read_index(index_path)
            self.dimension = self.index.d
            
            logger.info(f"Index loaded with {self.index.ntotal} vectors")
            return True
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False
