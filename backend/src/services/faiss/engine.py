"""
FAISS RAG Engine - Clean Architecture Implementation
Orchestrates FAISS vector DB components following clean architecture principles
"""
import os
import yaml
import logging
import time
import faiss
import numpy as np
import threading
from textwrap import dedent
from typing import List, Dict
from sentence_transformers import SentenceTransformer

from .core.chunking import FixedChunker, SemanticChunker
from .core.reranking import CrossEncoderReranker, BM25Reranker, HybridReranker, MMRReranker
from .vector import VectorSearchService
from .ingestion import DocumentIngestionService
from services.llm import BedrockService, GrokService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FaissRAGEngine:
    """FAISS Vector DB RAG Engine orchestrating all components"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize FAISS RAG Engine with all components.
        
        Sets up:
        - Embedding model (Titan/MiniLM) for vector generation
        - Chunking strategy (fixed or semantic) for document splitting
        - Vector search service (FAISS IndexFlatL2) for similarity search
        - Reranker (CrossEncoder/BM25/Hybrid/MMR) for result refinement
        - LLM services (Bedrock/Grok) for answer generation
        
        Args:
            config_path: Path to YAML config file (default: config.yaml)
            
        Raises:
            ValueError: If required config keys are missing
            FileNotFoundError: If config file doesn't exist
        """
        logger.info(f"Initializing FAISS RAG Engine with config: {config_path}")
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self._validate_config()
        self._index_lock = threading.Lock()
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {self.config['embeddings']['model']}")
        self.embedding_model = SentenceTransformer(self.config['embeddings']['model'])
        logger.info("Embedding model loaded successfully")
        
        # Initialize chunker
        chunk_method = self.config['embeddings'].get('chunk_method', 'fixed')
        logger.info(f"Chunking method: {chunk_method}")
        
        if chunk_method == 'semantic':
            threshold = self.config['embeddings'].get('semantic_threshold', 0.5)
            max_size = self.config['embeddings'].get('max_chunk_size', 1000)
            min_size = self.config['embeddings'].get('min_chunk_size', 100)
            self.chunker = SemanticChunker(self.embedding_model, threshold, max_size, min_size)
        else:
            self.chunker = FixedChunker(
                self.config['embeddings']['chunk_size'],
                self.config['embeddings']['chunk_overlap']
            )
        
        # Initialize services
        self.document_service = DocumentIngestionService(self.chunker)
        self.vector_search = VectorSearchService(self.embedding_model)
        
        # Initialize reranker
        self.reranker = None
        self.reranker_enabled = self.config.get('reranker', {}).get('enabled', False)
        self.reranker_method = None
        
        if self.reranker_enabled:
            self.reranker_method = self.config['reranker'].get('method', 'cross-encoder')
            logger.info(f"Reranker enabled: {self.reranker_method}")
            
            if self.reranker_method == 'cross-encoder':
                self.reranker = CrossEncoderReranker(self.config['reranker']['model'])
            elif self.reranker_method == 'mmr':
                mmr_lambda = self.config['reranker'].get('mmr_lambda', 0.7)
                self.reranker = MMRReranker(self.embedding_model, mmr_lambda)
        else:
            logger.info("Reranker disabled")
        
        # Initialize LLM services
        self.llm_services = []
        
        routing_model_id = self.config['bedrock'].get('routing_model_id')
        conversational_model_id = self.config['bedrock'].get('conversational_model_id')
        bedrock = BedrockService(
            self.config['bedrock']['region'],
            self.config['bedrock']['model_id'],
            routing_model_id,
            conversational_model_id
        )
        if bedrock.is_available():
            self.llm_services.append(('bedrock', bedrock))
        
        grok_config = self.config.get('grok', {})
        if grok_config.get('enabled', False):
            api_key = os.getenv('GROK_API_KEY') or grok_config.get('api_key', '').replace('${GROK_API_KEY}', os.getenv('GROK_API_KEY', ''))
            grok = GrokService(
                api_key,
                grok_config['base_url'],
                grok_config['model'],
                grok_config.get('max_tokens', 1000)
            )
            if grok.is_available():
                self.llm_services.append(('grok', grok))
        
        self.documents = []
        self.chunk_method = chunk_method
        
        logger.info("FAISS RAG Engine initialization complete")
    
    # ==================== CRUD OPERATIONS ====================
    
    def add_document_to_index(self, content: str, doc_id: str = None, auto_save: bool = True):
        """Add document to FAISS index"""
        with self._index_lock:
            original_docs = self.documents.copy()
            original_index = None
            
            try:
                if self.vector_search.index is None:
                    logger.info("Initializing empty FAISS index")
                    self.vector_search.dimension = self.embedding_model.get_sentence_embedding_dimension()
                    self.vector_search.index = faiss.IndexFlatL2(self.vector_search.dimension)
                else:
                    original_index = faiss.clone_index(self.vector_search.index)
                
                chunks = self.chunker.chunk(content) if self.chunk_method == 'semantic' else [content]
                
                # Add vectors to FAISS index
                self.vector_search.add_vectors(chunks)
                
                # Store documents with metadata
                for i, chunk in enumerate(chunks):
                    metadata = {'doc_id': doc_id, 'chunk_id': i}
                    self.documents.append({'text': chunk, 'metadata': metadata})
                
                self._rebuild_reranker()
                
                if auto_save:
                    self.save_index()
                
                logger.info(f"Added document {doc_id} ({len(chunks)} chunks)")
                return len(chunks)
            except Exception as e:
                logger.error(f"Failed to add document, rolling back: {e}")
                self.documents = original_docs
                if original_index:
                    self.vector_search.index = original_index
                raise
    
    def update_document_in_index(self, doc_id: str, content: str):
        """Update document in FAISS index"""
        with self._index_lock:
            original_docs = self.documents.copy()
            original_index = None
            
            if self.vector_search.index and self.vector_search.index.ntotal > 0:
                original_index = faiss.clone_index(self.vector_search.index)
            
            try:
                self._remove_document_no_lock(doc_id)
                self._add_document_no_lock(content, doc_id)
                logger.info(f"Updated document {doc_id}")
            except Exception as e:
                logger.error(f"Failed to update document, rolling back: {e}")
                self.documents = original_docs
                if original_index:
                    self.vector_search.index = original_index
                self.save_index()
                raise
    
    def remove_document_from_index(self, doc_id: str):
        """Remove document from FAISS index"""
        with self._index_lock:
            try:
                original_docs = self.documents.copy()
                self.documents = [doc for doc in self.documents if doc.get('metadata', {}).get('doc_id') != doc_id]
                
                if len(self.documents) == len(original_docs):
                    logger.warning(f"Document {doc_id} not found")
                    return
                
                if self.documents:
                    texts = [doc['text'] for doc in self.documents]
                    self.vector_search.build_index(texts)
                else:
                    self.vector_search.index = faiss.IndexFlatL2(self.vector_search.dimension)
                
                self._rebuild_reranker()
                self.save_index()
                
                logger.info(f"Removed document {doc_id} ({len(original_docs) - len(self.documents)} chunks)")
            except Exception as e:
                logger.error(f"Failed to remove document: {e}")
                self.documents = original_docs
                raise
    
    def save_index(self):
        """Save FAISS index and document metadata to disk"""
        if not self.config.get('faiss', {}).get('persist_index', False):
            return
        
        index_file = self.config['faiss'].get('index_file', './faiss_index/index.faiss')
        metadata_file = self.config['faiss'].get('metadata_file', './faiss_index/metadata.json')
        
        # Save FAISS index
        self.vector_search.save_index(index_file)
        
        # Save document metadata separately
        import json
        os.makedirs(os.path.dirname(metadata_file) or '.', exist_ok=True)
        with open(metadata_file, 'w') as f:
            json.dump({'documents': self.documents}, f)
        
        logger.info(f"Saved index and metadata")
    
    def load_index(self) -> bool:
        """Load FAISS index and document metadata from disk"""
        if not self.config.get('faiss', {}).get('persist_index', False):
            return False
        
        index_file = self.config['faiss'].get('index_file', './faiss_index/index.faiss')
        metadata_file = self.config['faiss'].get('metadata_file', './faiss_index/metadata.json')
        
        # Load FAISS index
        if not self.vector_search.load_index(index_file):
            return False
        
        # Load document metadata
        import json
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
                self.documents = data['documents']
            self._rebuild_reranker()
            logger.info(f"Loaded index with {len(self.documents)} documents")
            return True
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return False
    
    def ingest_documents(self, data_dir: str = "data"):
        """Ingest documents from directory"""
        self.documents = self.document_service.ingest_from_directory(data_dir)
        texts = [doc['text'] for doc in self.documents]
        self.vector_search.build_index(texts)
        self._rebuild_reranker()
    
    # ==================== QUERY OPERATIONS ====================
    
    def search(self, query: str) -> List[Dict]:
        """
        Search for relevant documents using vector similarity.
        
        Process:
        1. Vector search in FAISS index (cosine similarity)
        2. Optional reranking (CrossEncoder/BM25/Hybrid/MMR)
        3. Returns top-k most relevant documents
        
        Args:
            query: Search query text
            
        Returns:
            List of documents with text, metadata, and scores
            
        Example:
            results = engine.search("Lakers game score")
            # [{'text': '...', 'metadata': {...}, 'score': 0.85}, ...]
        """
        logger.info(f"Search query: '{query[:50]}...'")
        
        top_k = self.config.get('reranker', {}).get('top_k', 3) if self.reranker_enabled else self.config['faiss']['top_k']
        distance_threshold = self.config.get('faiss', {}).get('distance_threshold')
        
        # Get (index, score) tuples from vector search
        search_results = self.vector_search.search(query, top_k, distance_threshold=distance_threshold)
        
        # Map indices to documents
        results = []
        for idx, score in search_results:
            if idx < len(self.documents):
                results.append({
                    **self.documents[idx],
                    'score': score
                })
        
        logger.info(f"Retrieved {len(results)} candidates from FAISS")
        
        self._reranking_time = 0
        if self.reranker_enabled and len(results) > 0:
            rerank_start = time.time()
            logger.info("Applying reranking")
            final_k = self.config['reranker'].get('top_k', 3)
            score_threshold = self.config.get('reranker', {}).get('score_threshold')
            results = self.reranker.rerank(query, results, final_k, score_threshold=score_threshold)
            self._reranking_time = (time.time() - rerank_start) * 1000
            logger.info(f"Reranking complete in {self._reranking_time:.1f}ms, {len(results)} results")
        
        return results
    
    # ==================== PRIVATE METHODS ====================
    
    def _validate_config(self):
        """Validate required configuration keys"""
        required_keys = {
            'bedrock': ['region', 'model_id'],
            'embeddings': ['model', 'chunk_size', 'chunk_overlap'],
            'faiss': ['top_k']
        }
        
        for section, keys in required_keys.items():
            if section not in self.config:
                raise ValueError(f"Missing required config section: {section}")
            for key in keys:
                if key not in self.config[section]:
                    raise ValueError(f"Missing required config key: {section}.{key}")
        
        logger.debug("Config validation passed")
    
    def _rebuild_reranker(self):
        """Rebuild reranker after document changes"""
        if not self.reranker_enabled or not self.documents:
            return
        
        if self.reranker_method == 'bm25':
            self.reranker = BM25Reranker(self.documents)
        elif self.reranker_method == 'hybrid':
            ce_weight = self.config['reranker'].get('ce_weight', 0.7)
            bm25_weight = self.config['reranker'].get('bm25_weight', 0.3)
            self.reranker = HybridReranker(
                self.config['reranker']['model'],
                self.documents,
                ce_weight,
                bm25_weight
            )
        elif hasattr(self.reranker, 'documents'):
            self.reranker.documents = self.documents
    
    def _remove_document_no_lock(self, doc_id: str):
        """Remove without acquiring lock (internal use)"""
        original_count = len(self.documents)
        self.documents = [doc for doc in self.documents if doc.get('metadata', {}).get('doc_id') != doc_id]
        
        if len(self.documents) < original_count:
            if self.documents:
                texts = [doc['text'] for doc in self.documents]
                self.vector_search.build_index(texts)
            else:
                self.vector_search.index = faiss.IndexFlatL2(self.vector_search.dimension)
    
    def _add_document_no_lock(self, content: str, doc_id: str):
        """Add without acquiring lock (internal use)"""
        chunks = self.chunker.chunk(content) if self.chunk_method == 'semantic' else [content]
        
        # Add vectors to FAISS
        self.vector_search.add_vectors(chunks)
        
        # Store documents with metadata
        for i, chunk in enumerate(chunks):
            metadata = {'doc_id': doc_id, 'chunk_id': i}
            self.documents.append({'text': chunk, 'metadata': metadata})
        
        self._rebuild_reranker()
        self.save_index()
    
    @property
    def bedrock_available(self) -> bool:
        return any(name == 'bedrock' for name, _ in self.llm_services)
    
    @property
    def grok_available(self) -> bool:
        return any(name == 'grok' for name, _ in self.llm_services)
