"""FastAPI dependencies for dependency injection."""
from fastapi import Request
from typing import Optional


def get_faiss_rag(request: Request):
    """Get FAISS RAG engine from app state."""
    return request.app.state.faiss_rag


def get_doc_manager(request: Request):
    """Get document manager from app state."""
    return request.app.state.doc_manager


def get_web_search(request: Request):
    """Get web search service from app state."""
    return request.app.state.web_search


def get_metrics(request: Request):
    """Get metrics from app state."""
    return request.app.state.metrics


def get_cache_service(request: Request) -> Optional[object]:
    """Get cache service from app state."""
    return getattr(request.app.state, 'cache_service', None)


def get_query_usecase(request: Request):
    """Get query use case from app state (initialized at startup)."""
    return request.app.state.query_usecase



def get_feedback_collector(request: Request):
    """Get feedback collector from app state."""
    return request.app.state.feedback_collector


def get_query_preprocessor(request: Request):
    """Get query preprocessor from app state."""
    return request.app.state.query_preprocessor


def get_metrics_service(request: Request) -> Optional[object]:
    """Get metrics service from app state."""
    return getattr(request.app.state, 'metrics_service', None)


def get_query_optimizer(request: Request):
    """Get query optimizer."""
    from services.query import query_optimizer
    return query_optimizer


def get_xai_collections(request: Request):
    """Get xAI Collections client from app state."""
    return getattr(request.app.state, 'xai_collections', None)


def get_search_orchestrator(request: Request):
    """Get or create search orchestrator."""
    from orchestration import SearchOrchestrator
    
    web_search = get_web_search(request)
    rag = get_faiss_rag(request)
    cache = get_cache_service(request)
    xai_collections = get_xai_collections(request)
    return SearchOrchestrator(web_search, rag, cache, xai_collections=xai_collections)
