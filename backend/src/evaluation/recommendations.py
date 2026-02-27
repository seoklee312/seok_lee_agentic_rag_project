"""
Automated recommendations engine for optimal RAG configuration
"""
from typing import Dict, List
import numpy as np


class RecommendationEngine:
    """Generate data-driven recommendations for RAG configuration"""
    
    def __init__(self):
        self.thresholds = {
            'accuracy': 0.7,
            'latency_p95': 5.0,  # seconds
            'cost_per_query': 0.01  # dollars
        }
    
    def analyze_results(self, evaluation_results: Dict) -> Dict:
        """
        Analyze evaluation results and generate recommendations
        
        Args:
            evaluation_results: Results from model evaluation
            
        Returns:
            Recommendations dict with suggestions
        """
        recommendations = {
            'model': self._recommend_model(evaluation_results),
            'chunking': self._recommend_chunking(evaluation_results),
            'retrieval': self._recommend_retrieval(evaluation_results),
            'embedding': self._recommend_embedding(evaluation_results),
            'summary': []
        }
        
        # Generate summary
        recommendations['summary'] = self._generate_summary(recommendations)
        
        return recommendations
    
    def _recommend_model(self, results: Dict) -> Dict:
        """Recommend best Grok model based on metrics"""
        models = results.get('models', {})
        
        if not models:
            return {'recommendation': 'grok-3-mini', 'reason': 'Default choice'}
        
        # Score each model
        scores = {}
        for model_name, metrics in models.items():
            accuracy = metrics.get('accuracy', 0)
            latency = metrics.get('latency_p95', 10)
            cost = metrics.get('cost_per_query', 0.01)
            
            # Weighted score: 50% accuracy, 30% latency, 20% cost
            score = (
                0.5 * accuracy +
                0.3 * (1 / (1 + latency)) +  # Lower latency = higher score
                0.2 * (1 / (1 + cost * 100))  # Lower cost = higher score
            )
            scores[model_name] = score
        
        best_model = max(scores, key=scores.get)
        
        # Determine use case
        best_metrics = models[best_model]
        if best_metrics.get('accuracy', 0) > 0.85:
            use_case = 'production (high accuracy)'
        elif best_metrics.get('latency_p95', 10) < 3:
            use_case = 'development (fast)'
        else:
            use_case = 'balanced'
        
        return {
            'recommendation': best_model,
            'reason': f'Best overall score ({scores[best_model]:.2f}) for {use_case}',
            'alternatives': sorted(scores.items(), key=lambda x: x[1], reverse=True)[1:3]
        }
    
    def _recommend_chunking(self, results: Dict) -> Dict:
        """Recommend chunking strategy"""
        chunking_results = results.get('chunking', {})
        
        if not chunking_results:
            return {
                'recommendation': 'semantic',
                'reason': 'Default: preserves sentence boundaries',
                'chunk_size': 512,
                'overlap': 50
            }
        
        # Analyze retrieval quality by chunking method
        best_method = 'semantic'
        best_score = 0
        
        for method, metrics in chunking_results.items():
            mrr = metrics.get('mrr', 0)
            ndcg = metrics.get('ndcg', 0)
            score = 0.6 * mrr + 0.4 * ndcg
            
            if score > best_score:
                best_score = score
                best_method = method
        
        # Recommend chunk size based on query length
        avg_query_length = results.get('avg_query_length', 50)
        if avg_query_length > 100:
            chunk_size = 1024
        elif avg_query_length > 50:
            chunk_size = 512
        else:
            chunk_size = 256
        
        return {
            'recommendation': best_method,
            'reason': f'Best retrieval quality (score: {best_score:.2f})',
            'chunk_size': chunk_size,
            'overlap': int(chunk_size * 0.1)  # 10% overlap
        }
    
    def _recommend_retrieval(self, results: Dict) -> Dict:
        """Recommend retrieval configuration"""
        retrieval_results = results.get('retrieval', {})
        
        # Default recommendation
        if not retrieval_results:
            return {
                'recommendation': 'hybrid',
                'reason': 'Best of dense + sparse search',
                'top_k': 5,
                'reranking': 'cross-encoder'
            }
        
        # Analyze retrieval methods
        methods = {}
        for method, metrics in retrieval_results.items():
            precision = metrics.get('precision', 0)
            recall = metrics.get('recall', 0)
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            methods[method] = f1
        
        best_method = max(methods, key=methods.get) if methods else 'hybrid'
        
        # Recommend top_k based on query complexity
        avg_complexity = results.get('avg_query_complexity', 'medium')
        if avg_complexity == 'high':
            top_k = 10
        elif avg_complexity == 'low':
            top_k = 3
        else:
            top_k = 5
        
        return {
            'recommendation': best_method,
            'reason': f'Best F1 score ({methods.get(best_method, 0):.2f})',
            'top_k': top_k,
            'reranking': 'cross-encoder' if top_k > 5 else 'bm25'
        }
    
    def _recommend_embedding(self, results: Dict) -> Dict:
        """Recommend embedding configuration"""
        embedding_results = results.get('embeddings', {})
        
        # Check if dimension reduction would help
        avg_latency = results.get('avg_latency', 2.0)
        index_size = results.get('index_size', 1000)
        
        reduce_dimensions = False
        if avg_latency > 3.0 and index_size > 10000:
            reduce_dimensions = True
            reason = 'High latency with large index - dimension reduction recommended'
        else:
            reason = 'Current performance acceptable'
        
        return {
            'recommendation': 'all-MiniLM-L6-v2',
            'reason': 'Good balance of speed and quality',
            'reduce_dimensions': reduce_dimensions,
            'target_dimension': 128 if reduce_dimensions else 384,
            'explanation': reason
        }
    
    def _generate_summary(self, recommendations: Dict) -> List[str]:
        """Generate human-readable summary"""
        summary = []
        
        # Model recommendation
        model_rec = recommendations['model']
        summary.append(f"✅ Use {model_rec['recommendation']} - {model_rec['reason']}")
        
        # Chunking recommendation
        chunk_rec = recommendations['chunking']
        summary.append(
            f"✅ Use {chunk_rec['recommendation']} chunking with "
            f"{chunk_rec['chunk_size']} chars and {chunk_rec['overlap']} overlap"
        )
        
        # Retrieval recommendation
        retrieval_rec = recommendations['retrieval']
        summary.append(
            f"✅ Use {retrieval_rec['recommendation']} search with "
            f"top_k={retrieval_rec['top_k']} and {retrieval_rec['reranking']} reranking"
        )
        
        # Embedding recommendation
        embed_rec = recommendations['embedding']
        if embed_rec['reduce_dimensions']:
            summary.append(
                f"⚠️ Enable dimension reduction to {embed_rec['target_dimension']}D "
                f"- {embed_rec['explanation']}"
            )
        else:
            summary.append(f"✅ Keep current embedding configuration - {embed_rec['explanation']}")
        
        return summary
    
    def generate_config(self, recommendations: Dict) -> str:
        """Generate YAML config snippet from recommendations"""
        model_rec = recommendations['model']
        chunk_rec = recommendations['chunking']
        retrieval_rec = recommendations['retrieval']
        embed_rec = recommendations['embedding']
        
        config = f"""# Recommended Configuration (Auto-generated)

grok:
  model: {model_rec['recommendation']}

embeddings:
  chunk_method: {chunk_rec['recommendation']}
  chunk_size: {chunk_rec['chunk_size']}
  chunk_overlap: {chunk_rec['overlap']}
  reduce_dimensions: {str(embed_rec['reduce_dimensions']).lower()}
  target_dimension: {embed_rec['target_dimension']}

retrieval:
  method: {retrieval_rec['recommendation']}
  top_k: {retrieval_rec['top_k']}
  reranking: {retrieval_rec['reranking']}

# Reasoning:
# - Model: {model_rec['reason']}
# - Chunking: {chunk_rec['reason']}
# - Retrieval: {retrieval_rec['reason']}
# - Embedding: {embed_rec['explanation']}
"""
        return config


# Global instance
recommendation_engine = RecommendationEngine()
