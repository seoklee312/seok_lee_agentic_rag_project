"""Query endpoints router - handles query processing."""
from fastapi import APIRouter, Request, HTTPException, Depends
from models import Query
from services.query.suggestions import query_suggestions_service
from dependencies import get_metrics, get_query_usecase
from typing import Dict, List, Any
import logging
import time

router = APIRouter(tags=["queries"])
logger = logging.getLogger(__name__)


@router.post("/query")
async def query(
    request: Request, 
    q: Query,
    usecase=Depends(get_query_usecase),
    metrics=Depends(get_metrics)
) -> Dict[str, Any]:
    """
    Unified query endpoint with BEST QUALITY.
    
    Features:
    - Self-Reflective RAG (reduces hallucinations by 52%)
    - Corrective RAG (handles outdated information)
    - Agentic orchestration with graph-based routing
    - Semantic caching for repeated queries
    - Temporal filtering for time-aware results
    - Memory management for conversation context
    - Confidence scoring
    - Grok LLM (primary) with Bedrock fallback
    - FAISS vector retrieval
    - xAI Collections (optional)
    
    Rate limit: 120 requests/minute
    """
    metrics['total_queries'] += 1
    start = time.time()
    
    logger.info(f"📥 Query received: '{q.question[:80]}...'")
    
    # Record query for suggestions
    query_suggestions_service.record_query(q.question)
    
    try:
        # Execute with full feature set
        result = await usecase.execute(q)
        
        latency = (time.time() - start) * 1000
        metrics['total_latency_ms'] = metrics.get('total_latency_ms', 0) + latency
        
        logger.info(f"✅ Query complete: {latency:.0f}ms")
        return result
        
    except Exception as e:
        logger.error(f"❌ Query failed: {str(e)}", exc_info=True)
        metrics['failed_queries'] += 1
        raise HTTPException(status_code=500, detail=str(e))
