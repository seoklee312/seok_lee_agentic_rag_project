"""
System monitoring endpoints router
"""
from fastapi import APIRouter, Request, Depends
from dependencies import get_faiss_rag, get_doc_manager, get_feedback_collector, get_query_preprocessor, get_metrics
import time
import logging

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health(
    request: Request,
    rag=Depends(get_faiss_rag),
    metrics=Depends(get_metrics)
):
    """Enhanced health check with all services"""
    start_time = request.app.state.start_time
    uptime = time.time() - (start_time or time.time())
    avg_latency = metrics['total_latency'] / max(metrics['successful_queries'], 1)
    
    # Get services from app state
    doc_manager = request.app.state.doc_manager
    feedback_collector = request.app.state.feedback_collector
    query_preprocessor = request.app.state.query_preprocessor
    
    # Safe index access
    index_size = 0
    if rag and rag.vector_search.index:
        index_size = rag.vector_search.index.ntotal
    
    return {
        "status": "healthy",
        "uptime_seconds": round(uptime, 2),
        "services": {
            "rag_engine": rag is not None,
            "document_manager": doc_manager is not None,
            "feedback_collector": feedback_collector is not None,
            "query_preprocessor": query_preprocessor is not None
        },
        "documents_indexed": index_size,
        "index_size": index_size,
        "bedrock_available": any(name == 'bedrock' for name, _ in (rag.llm_services if rag else [])),
        "grok_available": any(name == 'grok' for name, _ in (rag.llm_services if rag else [])),
        "reranker_enabled": rag.reranker_method != 'none' if rag else False,
        "metrics": {
            "total_queries": metrics['total_queries'],
            "success_rate": round(metrics['successful_queries'] / max(metrics['total_queries'], 1) * 100, 2),
            "avg_latency_ms": round(avg_latency * 1000, 2),
            "cache_hit_rate": round(metrics['cache_hits'] / max(metrics['total_queries'], 1) * 100, 2),
            "documents_managed": metrics['documents_created'] + metrics['documents_updated'] + metrics['documents_deleted'],
            "feedback_count": metrics['feedback_submitted']
        }
    }

@router.get("/metrics")
async def get_metrics_endpoint(request: Request):
    """Detailed metrics endpoint with time-series data and cache stats"""
    # Get metrics from app state
    metrics = request.app.state.metrics
    start_time = request.app.state.start_time
    
    # Get time-series metrics
    if hasattr(request.app.state, 'metrics_service'):
        ts_metrics = request.app.state.metrics_service.get_metrics()
    else:
        ts_metrics = {
            "totals": {},
            "rates": {},
            "time_series": {}
        }
    
    # Get cache stats
    cache_stats = {"enabled": False}
    if hasattr(request.app.state, 'cache_service'):
        cache = request.app.state.cache_service
        if cache.enabled and cache.client:
            try:
                info = cache.client.info('stats')
                cache_stats = {
                    "enabled": True,
                    "hits": info.get('keyspace_hits', 0),
                    "misses": info.get('keyspace_misses', 0),
                    "hit_rate": round(info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100, 2),
                    "keys": cache.client.dbsize()
                }
            except:
                cache_stats = {"enabled": True, "error": "Could not fetch stats"}
    
    uptime = time.time() - (start_time or time.time())
    avg_latency = metrics['total_latency'] / max(metrics['successful_queries'], 1)
    success_rate = metrics['successful_queries'] / max(metrics['total_queries'], 1) * 100
    
    return {
        "uptime_seconds": round(uptime, 2),
        "queries": {
            "total": metrics['total_queries'],
            "successful": metrics['successful_queries'],
            "failed": metrics['failed_queries'],
            "success_rate": round(success_rate, 2),
            "avg_latency_ms": round(avg_latency * 1000, 2),
            "cache_hits": metrics['cache_hits'],
            "cache_hit_rate": round(metrics['cache_hits'] / max(metrics['total_queries'], 1) * 100, 2),
            "preprocessed": metrics['queries_preprocessed']
        },
        "documents": {
            "created": metrics['documents_created'],
            "updated": metrics['documents_updated'],
            "deleted": metrics['documents_deleted'],
            "total_operations": metrics['documents_created'] + metrics['documents_updated'] + metrics['documents_deleted']
        },
        "feedback": {
            "submitted": metrics['feedback_submitted']
        },
        "cache": cache_stats,
        "time_series": ts_metrics
    }
