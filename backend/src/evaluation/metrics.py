"""
Metrics calculator for model evaluation
"""
import time
from typing import List, Dict, Any
import numpy as np


class MetricsCalculator:
    """Calculate evaluation metrics"""
    
    @staticmethod
    def keyword_accuracy(response: str, expected_keywords: List[str]) -> float:
        """Calculate keyword match accuracy"""
        response_lower = response.lower()
        matches = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
        return matches / len(expected_keywords) if expected_keywords else 0.0
    
    @staticmethod
    def calculate_mrr(results: List[Dict[str, Any]]) -> float:
        """Mean Reciprocal Rank"""
        reciprocal_ranks = []
        for result in results:
            accuracy = result.get('accuracy', 0)
            # If accuracy > 0.5, consider it relevant at rank 1
            rr = 1.0 if accuracy > 0.5 else 0.0
            reciprocal_ranks.append(rr)
        return np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
    
    @staticmethod
    def calculate_ndcg(results: List[Dict[str, Any]], k: int = 5) -> float:
        """Normalized Discounted Cumulative Gain"""
        relevance_scores = [r.get('accuracy', 0) for r in results[:k]]
        
        # DCG
        dcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(relevance_scores))
        
        # IDCG (ideal)
        ideal_scores = sorted(relevance_scores, reverse=True)
        idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_scores))
        
        return dcg / idcg if idcg > 0 else 0.0
    
    @staticmethod
    def aggregate_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate all metrics"""
        if not results:
            return {
                'avg_accuracy': 0.0,
                'min_accuracy': 0.0,
                'max_accuracy': 0.0,
                'mrr': 0.0,
                'ndcg@5': 0.0,
                'avg_latency': 0.0,
                'p50_latency': 0.0,
                'p95_latency': 0.0,
                'p99_latency': 0.0,
                'total_queries': 0
            }
        
        accuracies = [r['accuracy'] for r in results]
        latencies = [r['latency'] for r in results]
        
        return {
            'avg_accuracy': np.mean(accuracies),
            'min_accuracy': np.min(accuracies),
            'max_accuracy': np.max(accuracies),
            'mrr': MetricsCalculator.calculate_mrr(results),
            'ndcg@5': MetricsCalculator.calculate_ndcg(results, k=5),
            'avg_latency': np.mean(latencies),
            'p50_latency': np.percentile(latencies, 50),
            'p95_latency': np.percentile(latencies, 95),
            'p99_latency': np.percentile(latencies, 99),
            'total_queries': len(results)
        }
