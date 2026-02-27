"""Query Service - Business logic for query processing."""
from typing import Dict, Any, TYPE_CHECKING
from models import Query
from services.state import MemoryManager
from .temporal_filter import TemporalFilter
from .optimizer import QueryOptimizer
from .domain_detector import DomainDetector
from .intent_classifier import IntentClassifier
import logging
import time

if TYPE_CHECKING:
    from orchestration import AgenticRAGOrchestrator

logger = logging.getLogger(__name__)


class QueryService:
    """
    Query Service - Business logic layer.
    
    Flow:
    1. Classify intent (conversational vs domain_query)
    2. If conversational → chat only
    3. If domain_query → detect domain → agentic orchestration
    """
    
    def __init__(
        self,
        agentic_orchestrator: 'AgenticRAGOrchestrator',
        temporal_filter: TemporalFilter,
        memory_manager: MemoryManager,
        query_optimizer: QueryOptimizer,
        domain_detector: DomainDetector,
        intent_classifier: IntentClassifier,
        grok_client
    ):
        self.agentic_orchestrator = agentic_orchestrator
        self.temporal_filter = temporal_filter
        self.memory_manager = memory_manager
        self.query_optimizer = query_optimizer
        self.domain_detector = domain_detector
        self.intent_classifier = intent_classifier
        self.grok_client = grok_client
    
    async def process_query(self, query: Query) -> Dict[str, Any]:
        """
        Process query with intent classification and domain detection.
        
        Flow:
        1. Classify intent
        2. Conversational → chat only
        3. Domain query → detect domain → agentic orchestration (web + RAG)
        """
        start_time = time.time()
        step_timings = {}
        
        # Step 1: Classify intent
        step_start = time.time()
        intent = await self.intent_classifier.classify(query.question)
        step_timings['intent_classification'] = (time.time() - step_start) * 1000
        
        # Step 2: Handle conversational queries (no retrieval)
        if intent == "conversational":
            return await self._handle_conversational(query.question, start_time, step_timings)
        
        # Step 3: Domain detection for domain queries
        step_start = time.time()
        domain_info = await self.domain_detector.detect_domain(query.question)
        step_timings['domain_detection'] = (time.time() - step_start) * 1000
        
        logger.info(f"🎯 Domain: {domain_info['domain']} (configured: {domain_info['is_configured']})")
        
        # Step 4: Add memory context
        memory_context = self.memory_manager.get_context(query.question)
        if memory_context:
            logger.info(f"Using memory context: {len(memory_context)} chars")
        
        # Step 3: Execute agentic orchestration
        
        # Step 5: Execute agentic orchestration (web + RAG always for domain queries)
        step_start = time.time()
        agentic_result = await self.agentic_orchestrator.execute(
            question=query.question,
            system_prompt=domain_info['system_prompt'],
            domain=domain_info['domain']
        )
        step_timings['agentic_orchestration'] = (time.time() - step_start) * 1000
        
        logger.info(f"Agentic orchestration complete")
        
        # Step 6: Extract and format result
        if 'answer' in agentic_result and agentic_result['answer']:
            result = {
                'answer': agentic_result['answer'],
                'domain': domain_info['domain'],
                'is_configured_domain': domain_info['is_configured'],
                'mode': 'agentic',
                'confidence': 'HIGH' if agentic_result.get('metadata', {}).get('grade_score', 0) >= 0.7 else 'MEDIUM',
                'sources': agentic_result.get('sources', []),
                'metadata': agentic_result.get('metadata', {})
            }
            
            # Step 7: Apply temporal filtering
            temporal_intent = self.temporal_filter.extract_temporal_intent(query.question)
            if temporal_intent['is_temporal']:
                result['sources'] = self.temporal_filter.process_query(query.question, result['sources'])
                logger.info(f"Applied temporal filtering")
        else:
            # Fallback
            logger.warning("Agentic orchestrator returned no answer")
            result = {
                'answer': "I couldn't generate an answer. Please try rephrasing your question.",
                'domain': domain_info['domain'],
                'mode': 'fallback',
                'confidence': 'LOW',
                'sources': [],
                'metadata': {}
            }
        
        # Add timings
        total_time = (time.time() - start_time) * 1000
        result['total_latency_ms'] = int(total_time)
        result['step_timings'] = {k: round(v, 2) for k, v in step_timings.items()}
        
        # Update memory
        self.memory_manager.add_interaction(query.question, result['answer'])
        
        return result
    
    async def _handle_conversational(self, question: str, start_time: float, step_timings: Dict) -> Dict[str, Any]:
        """Handle conversational queries without retrieval."""
        logger.info("💬 Handling conversational query (no retrieval)")
        
        step_start = time.time()
        
        try:
            response = await self.grok_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a friendly, helpful AI assistant. Be conversational and warm."},
                    {"role": "user", "content": question}
                ],
                model="grok-3-mini",
                max_tokens=512
            )
            
            answer = response['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Conversational response failed: {e}")
            answer = "Hello! I'm here to help. What would you like to know?"
        
        step_timings['conversational_response'] = (time.time() - step_start) * 1000
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            'answer': answer,
            'domain': None,
            'mode': 'conversational',
            'confidence': 'HIGH',
            'sources': [],
            'metadata': {},
            'total_latency_ms': int(total_time),
            'step_timings': {k: round(v, 2) for k, v in step_timings.items()}
        }

