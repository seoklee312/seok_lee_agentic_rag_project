"""
Model evaluator for comparing Grok models
"""
import asyncio
import time
from typing import List, Dict, Any
import logging
from .benchmark_data import ALL_QUERIES
from .metrics import MetricsCalculator

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Evaluate and compare Grok models"""
    
    def __init__(self, grok_client, domain_manager):
        self.grok_client = grok_client
        self.domain_manager = domain_manager
        self.metrics_calc = MetricsCalculator()
    
    async def evaluate_query(self, query_data: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Evaluate single query"""
        # Switch domain
        domain = self.domain_manager.switch_domain(query_data['domain'])
        
        # Prepare messages
        messages = [
            {"role": "system", "content": domain.get_system_prompt()},
            {"role": "user", "content": query_data['query']}
        ]
        
        # Time the query
        start = time.time()
        try:
            response = await self.grok_client.chat_completion(
                messages=messages,
                model=model,
                max_tokens=300
            )
            latency = time.time() - start
            
            # Calculate accuracy
            content = response['content']
            accuracy = self.metrics_calc.keyword_accuracy(
                content, 
                query_data['expected_keywords']
            )
            
            return {
                'query': query_data['query'],
                'domain': query_data['domain'],
                'model': model,
                'accuracy': accuracy,
                'latency': latency,
                'response': content[:200],
                'tokens': response['usage'].get('total_tokens', 0),
                'success': True
            }
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {
                'query': query_data['query'],
                'domain': query_data['domain'],
                'model': model,
                'accuracy': 0.0,
                'latency': time.time() - start,
                'error': str(e),
                'success': False
            }
    
    async def evaluate_model(self, model: str, queries: List[Dict] = None) -> Dict[str, Any]:
        """Evaluate a model on all queries"""
        queries = queries or ALL_QUERIES
        logger.info(f"Evaluating {model} on {len(queries)} queries")
        
        results = []
        for query_data in queries:
            result = await self.evaluate_query(query_data, model)
            results.append(result)
            await asyncio.sleep(0.1)  # Rate limiting
        
        # Aggregate metrics
        successful = [r for r in results if r['success']]
        metrics = self.metrics_calc.aggregate_metrics(successful)
        
        return {
            'model': model,
            'metrics': metrics,
            'results': results,
            'success_rate': len(successful) / len(results)
        }
    
    async def compare_models(self, models: List[str], queries: List[Dict] = None) -> Dict[str, Any]:
        """Compare multiple models"""
        logger.info(f"Comparing models: {models}")
        
        evaluations = {}
        for model in models:
            eval_result = await self.evaluate_model(model, queries)
            evaluations[model] = eval_result
        
        # Generate comparison
        comparison = {
            'models': models,
            'evaluations': evaluations,
            'winner': self._determine_winner(evaluations)
        }
        
        return comparison
    
    def _determine_winner(self, evaluations: Dict[str, Any]) -> Dict[str, str]:
        """Determine best model for each metric"""
        winners = {}
        
        # Best accuracy
        best_acc = max(evaluations.items(), 
                      key=lambda x: x[1]['metrics']['avg_accuracy'])
        winners['accuracy'] = best_acc[0]
        
        # Best latency
        best_lat = min(evaluations.items(),
                      key=lambda x: x[1]['metrics']['avg_latency'])
        winners['latency'] = best_lat[0]
        
        # Best MRR
        best_mrr = max(evaluations.items(),
                      key=lambda x: x[1]['metrics']['mrr'])
        winners['mrr'] = best_mrr[0]
        
        return winners
