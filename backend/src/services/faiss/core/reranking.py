"""
Advanced reranking strategies for search results
"""
import logging
import numpy as np
import re
from typing import List, Dict
from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


def tokenize_text(text: str) -> List[str]:
    """Shared tokenization with stopword removal"""
    tokens = re.findall(r'\b\w+\b', text.lower())
    return [t for t in tokens if len(t) > 2]


class Reranker:
    """Base class for reranking"""
    
    def rerank(self, query: str, results: List[Dict], top_k: int) -> List[Dict]:
        raise NotImplementedError


class CrossEncoderReranker(Reranker):
    """Cross-encoder with score normalization"""
    
    def __init__(self, model_name: str):
        logger.info(f"Loading cross-encoder: {model_name}")
        self.model = CrossEncoder(model_name)
        logger.info("Cross-encoder loaded successfully")
    
    def rerank(self, query: str, results: List[Dict], top_k: int, score_threshold: float = None) -> List[Dict]:
        if not results:
            return []
        
        pairs = [[query, doc['text']] for doc in results]
        scores = self.model.predict(pairs)
        
        # Normalize scores to 0-1 range
        scores = np.array(scores)
        if scores.max() != scores.min():
            scores = (scores - scores.min()) / (scores.max() - scores.min())
        else:
            # All scores identical, set to 0.5
            scores = np.full_like(scores, 0.5)
        
        for i, doc in enumerate(results):
            doc['rerank_score'] = float(scores[i])
        
        # Apply score threshold if provided
        if score_threshold is not None:
            results = [doc for doc in results if doc['rerank_score'] >= score_threshold]
            logger.info(f"Filtered to {len(results)} results above threshold {score_threshold}")
        
        results = sorted(results, key=lambda x: x['rerank_score'], reverse=True)
        return results[:top_k]


class BM25Reranker(Reranker):
    """BM25 with better tokenization"""
    
    def __init__(self, documents: List[Dict]):
        logger.info("Initializing BM25 reranker...")
        tokenized_corpus = [tokenize_text(doc['text']) for doc in documents]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.documents = documents
        logger.info("BM25 reranker initialized")
    
    def rerank(self, query: str, results: List[Dict], top_k: int, score_threshold: float = None) -> List[Dict]:
        if not results:
            return []
        
        tokenized_query = tokenize_text(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # Normalize BM25 scores to 0-1
        bm25_scores = np.array(bm25_scores)
        if bm25_scores.max() != bm25_scores.min():
            bm25_scores = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min())
        
        for doc in results:
            # Find document index safely
            doc_idx = None
            for i, d in enumerate(self.documents):
                if d['text'] == doc['text']:
                    doc_idx = i
                    break
            
            if doc_idx is not None:
                doc['rerank_score'] = float(bm25_scores[doc_idx])
            else:
                logger.warning(f"Document not found in BM25 corpus, using score 0")
                doc['rerank_score'] = 0.0
        
        # Apply score threshold if provided
        if score_threshold is not None:
            results = [doc for doc in results if doc['rerank_score'] >= score_threshold]
            logger.info(f"Filtered to {len(results)} results above threshold {score_threshold}")
        
        results = sorted(results, key=lambda x: x['rerank_score'], reverse=True)
        return results[:top_k]


class HybridReranker(Reranker):
    """Combines Cross-Encoder + BM25 for best results"""
    
    def __init__(self, cross_encoder_model: str, documents: List[Dict], 
                 ce_weight: float = 0.7, bm25_weight: float = 0.3):
        logger.info("Initializing hybrid reranker (Cross-Encoder + BM25)")
        self.cross_encoder = CrossEncoderReranker(cross_encoder_model)
        self.bm25 = BM25Reranker(documents)
        self.ce_weight = ce_weight
        self.bm25_weight = bm25_weight
        logger.info(f"Hybrid weights: CE={ce_weight}, BM25={bm25_weight}")
    
    def rerank(self, query: str, results: List[Dict], top_k: int, score_threshold: float = None) -> List[Dict]:
        if not results:
            return []
        
        # Get Cross-Encoder scores (without threshold yet)
        ce_results = self.cross_encoder.rerank(query, results.copy(), len(results), score_threshold=None)
        ce_scores = {doc['text']: doc['rerank_score'] for doc in ce_results}
        
        # Get BM25 scores (without threshold yet)
        bm25_results = self.bm25.rerank(query, results.copy(), len(results), score_threshold=None)
        bm25_scores = {doc['text']: doc['rerank_score'] for doc in bm25_results}
        
        # Combine scores
        for doc in results:
            ce_score = ce_scores.get(doc['text'], 0.0)
            bm25_score = bm25_scores.get(doc['text'], 0.0)
            doc['rerank_score'] = (self.ce_weight * ce_score) + (self.bm25_weight * bm25_score)
        
        # Apply score threshold if provided
        if score_threshold is not None:
            results = [doc for doc in results if doc['rerank_score'] >= score_threshold]
            logger.info(f"Filtered to {len(results)} results above threshold {score_threshold}")
        
        results = sorted(results, key=lambda x: x['rerank_score'], reverse=True)
        return results[:top_k]
        for doc in results:
            text = doc['text']
            ce_score = ce_scores.get(text, 0)
            bm25_score = bm25_scores.get(text, 0)
            doc['rerank_score'] = (
                self.ce_weight * ce_score + 
                self.bm25_weight * bm25_score
            )
            doc['ce_score'] = ce_score
            doc['bm25_score'] = bm25_score
        
        results = sorted(results, key=lambda x: x['rerank_score'], reverse=True)
        return results[:top_k]


class MMRReranker(Reranker):
    """Maximal Marginal Relevance - balances relevance and diversity"""
    
    def __init__(self, embedding_model, lambda_param: float = 0.7):
        self.embedding_model = embedding_model
        self.lambda_param = lambda_param  # 1.0 = pure relevance, 0.0 = pure diversity
        logger.info(f"MMR reranker initialized (lambda={lambda_param})")
    
    def rerank(self, query: str, results: List[Dict], top_k: int, score_threshold: float = None) -> List[Dict]:
        if not results:
            return []
        
        # Encode query and documents
        query_emb = self.embedding_model.encode([query])[0]
        doc_embs = self.embedding_model.encode([doc['text'] for doc in results])
        
        # Calculate relevance scores
        relevance = np.array([
            np.dot(query_emb, doc_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(doc_emb))
            for doc_emb in doc_embs
        ])
        
        # MMR selection
        selected = []
        remaining = list(range(len(results)))
        
        while len(selected) < top_k and remaining:
            mmr_scores = []
            
            for idx in remaining:
                # Relevance component
                rel_score = relevance[idx]
                
                # Diversity component (max similarity to already selected)
                if selected:
                    similarities = [
                        np.dot(doc_embs[idx], doc_embs[s]) / 
                        (np.linalg.norm(doc_embs[idx]) * np.linalg.norm(doc_embs[s]))
                        for s in selected
                    ]
                    max_sim = max(similarities)
                else:
                    max_sim = 0
                
                # MMR score
                mmr = self.lambda_param * rel_score - (1 - self.lambda_param) * max_sim
                mmr_scores.append((idx, mmr))
            
            # Select best MMR score
            best_idx, best_score = max(mmr_scores, key=lambda x: x[1])
            selected.append(best_idx)
            remaining.remove(best_idx)
        
        # Return reranked results
        reranked = [results[i] for i in selected]
        for i, doc in enumerate(reranked):
            doc['rerank_score'] = float(relevance[selected[i]])
            doc['mmr_rank'] = i + 1
        
        # Apply score threshold if provided
        if score_threshold is not None:
            reranked = [doc for doc in reranked if doc['rerank_score'] >= score_threshold]
            logger.info(f"Filtered to {len(reranked)} results above threshold {score_threshold}")
        
        return reranked
