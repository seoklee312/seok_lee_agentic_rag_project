"""
RAG System API - Main Application
Uses FastAPI routers for clean separation
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import yaml
import logging
import os
import time
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="RAG System API", version="1.0.0")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
# Global variable (removed - now using app.state)
doc_manager = None
feedback_collector = None
query_preprocessor = None
start_time = time.time()

# Metrics
metrics = {
    'total_queries': 0,
    'successful_queries': 0,
    'failed_queries': 0,
    'total_latency': 0.0,
    'cache_hits': 0,
    'documents_created': 0,
    'documents_updated': 0,
    'documents_deleted': 0,
    'feedback_submitted': 0,
    'queries_preprocessed': 0
}

@app.on_event("startup")
async def startup_event():
    """Initialize RAG system and services"""
    global doc_manager, feedback_collector, query_preprocessor
    
    from services.faiss import FaissRAGEngine, DocumentManager
    from services.feedback import FeedbackCollector
    from services.query import QueryPreprocessor
    from services.web_search import WebSearchService
    from services.monitoring import metrics_service
    from services.cache import CacheService
    from services.cache import redis as cache_module
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    import re
    
    def _expand_env_vars(config):
        """Recursively expand ${VAR} in config values."""
        if isinstance(config, dict):
            return {k: _expand_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [_expand_env_vars(item) for item in config]
        elif isinstance(config, str):
            return re.sub(r'\$\{(\w+)\}', lambda m: os.getenv(m.group(1), m.group(0)), config)
        return config
    
    logger.info("Starting RAG system initialization")
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
        
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Expand environment variables
        config = _expand_env_vars(config)
        
        # Configure thread pool for blocking operations
        thread_pool_size = config.get('application', {}).get('thread_pool_size', 32)
        loop = asyncio.get_event_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=thread_pool_size))
        logger.info(f"Thread pool configured with {thread_pool_size} workers")
        
        # Initialize Grok client (PRIMARY) with Bedrock fallback
        from services.grok_client import GrokClient
        from services.grok_adapter import GrokLLMAdapter
        from services.xai_collections import XAICollectionsClient
        
        grok_config = config.get('grok', {})
        bedrock_config = config.get('bedrock', {})
        
        # Initialize Bedrock as fallback (if configured)
        bedrock_fallback = None
        if bedrock_config.get('fallback', False):
            try:
                from services.faiss import FaissRAGEngine
                temp_faiss = FaissRAGEngine(config_path)
                # Get Bedrock LLM service from FAISS engine
                if temp_faiss.llm_services:
                    bedrock_fallback = temp_faiss.llm_services[0][1]
                    logger.info("Bedrock fallback initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Bedrock fallback: {e}")
        
        # Initialize Grok as primary LLM
        grok_client = GrokClient(grok_config, bedrock_fallback=bedrock_fallback)
        grok_llm = GrokLLMAdapter(grok_client)  # Wrap with adapter
        app.state.grok_client = grok_client
        app.state.grok_llm = grok_llm  # Store adapted version
        logger.info("Grok client initialized as PRIMARY LLM")
        
        # Initialize xAI Collections (if enabled)
        xai_collections_config = config.get('xai_collections', {})
        xai_collections = None
        if xai_collections_config.get('enabled', False):
            try:
                logger.info(f"xAI Collections config: {xai_collections_config.get('collections', {})}")
                xai_collections = XAICollectionsClient(xai_collections_config)
                app.state.xai_collections = xai_collections
                logger.info("xAI Collections initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize xAI Collections: {e}")
        
        # Initialize cache service with config
        cache_service = CacheService(config.get('redis', {}))
        cache_module.cache_service = cache_service
        
        # Initialize services (keep FAISS for now as fallback to Collections)
        faiss_rag = FaissRAGEngine(config_path)
        doc_manager = DocumentManager()  # Uses default storage_path
        feedback_collector = FeedbackCollector()  # Uses default storage_path
        query_preprocessor = QueryPreprocessor(config)  # Pass config
        web_search_service = WebSearchService(config.get('web_search', {}))
        
        # Store services in app state
        app.state.faiss_rag = faiss_rag
        app.state.doc_manager = doc_manager
        app.state.feedback_collector = feedback_collector
        app.state.query_preprocessor = query_preprocessor
        app.state.web_search = web_search_service
        app.state.metrics = metrics
        app.state.metrics_service = metrics_service
        app.state.cache_service = cache_service
        app.state.limiter = limiter
        app.state.start_time = start_time
        app.state.config = config  # Store config for access in routers
        
        # Initialize query optimizer with Grok (PRIMARY)
        from services.query import QueryOptimizer
        query_optimizer_instance = QueryOptimizer(grok_llm, config)  # Use adapter
        logger.info("Query optimizer initialized with Grok")
        
        # Initialize query usecase (fix race condition)
        from usecases.query_usecase import QueryUseCase
        from services.query import QueryService
        from orchestration import AgenticRAGOrchestrator, SearchOrchestrator
        from services.query import TemporalFilter
        from services.state import MemoryManager
        from services.cache import SemanticCache
        
        # Create semantic cache
        semantic_cache = None
        if hasattr(faiss_rag, 'embedding_model') and faiss_rag.embedding_model:
            semantic_cache = SemanticCache(faiss_rag.embedding_model, threshold=0.95, ttl=3600)
        
        # Initialize xAI Collections client
        from services.xai_collections import XAICollectionsClient
        xai_collections_config = {
            'api_key': os.getenv("XAI_API_KEY"),
            'enabled': True
        }
        xai_collections_client = XAICollectionsClient(xai_collections_config)
        logger.info("xAI Collections client initialized")
        
        # Initialize domain manager EARLY (needed by domain detector)
        from domains import DomainManager
        domains_path = os.path.join(os.path.dirname(__file__), 'domains')
        domain_manager = DomainManager(domains_path, xai_collections_client)
        app.state.domain_manager = domain_manager
        logger.info("Domain manager initialized")
        
        # Create search orchestrator with xAI Collections
        logger.info(f"Creating SearchOrchestrator with xAI Collections support")
        search_orchestrator = SearchOrchestrator(
            web_search_service,
            faiss_rag,
            cache_service,
            query_optimizer_instance,
            xai_collections=xai_collections_client
        )
        app.state.search_orchestrator = search_orchestrator
        app.state.query_optimizer = query_optimizer_instance
        
        # Create services
        temporal_filter = TemporalFilter()
        memory_manager = MemoryManager(vector_store=None)
        
        # Use Grok as primary LLM with SearchOrchestrator (has xAI Collections built-in)
        agentic_orchestrator = AgenticRAGOrchestrator(
            llm=grok_llm,
            retriever=faiss_rag,  # FAISS as fallback
            web_search_agent=search_orchestrator,  # Has xAI Collections + Web
            cache=semantic_cache
        )
        
        # Initialize intent classifier and domain detector
        from services.query.intent_classifier import IntentClassifier
        from services.query.domain_detector import DomainDetector
        
        intent_classifier = IntentClassifier(grok_client)
        domain_detector = DomainDetector(grok_client, domain_manager)
        domain_detector.xai_collections = xai_collections  # Add xAI Collections for RAG-based detection
        
        logger.info("Intent classifier and domain detector initialized")
        
        query_service = QueryService(
            agentic_orchestrator=agentic_orchestrator,
            temporal_filter=temporal_filter,
            memory_manager=memory_manager,
            query_optimizer=query_optimizer_instance,
            domain_detector=domain_detector,
            intent_classifier=intent_classifier,
            grok_client=grok_client
        )
        
        # Create and cache query usecase
        query_usecase = QueryUseCase(query_service=query_service)
        app.state.query_usecase = query_usecase
        logger.info("Query usecase initialized at startup")
        
        # Load index from disk
        faiss_rag.load_index()
        logger.info("FAISS RAG Engine ready - add documents via API")
        
        # Set default domain
        try:
            domain_manager.switch_domain('medical')
            logger.info("Default domain set to: medical")
        except Exception as e:
            logger.warning(f"Failed to set default domain: {e}")
        
        logger.info("Hybrid RAG system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown - save index"""
    logger.info("Shutting down RAG system")
    if hasattr(app.state, 'faiss_rag'):
        try:
            app.state.faiss_rag.save_index()
            logger.info("FAISS index saved successfully")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve frontend HTML"""
    html_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'templates', 'frontend.html')
    with open(html_path, "r") as f:
        return f.read()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

# Legacy endpoint
@app.post("/query")
async def query_legacy(q):
    """Legacy query endpoint"""
    from routers.query import query_v1
    from fastapi import Request
    return await query_v1(Request, q)

# Include routers
from routers import query, documents, feedback, system, domain

app.include_router(query.router, prefix="/v1")
app.include_router(documents.router, prefix="/v1")
app.include_router(feedback.router, prefix="/v1")
app.include_router(system.router, prefix="/v1")
app.include_router(domain.router, prefix="/v1")  # Domain router

# Mount static files (must be after routes)
static_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'static')
app.mount("/static", StaticFiles(directory=static_path), name="static")

if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    logger.info(f"Starting server on {config['server']['host']}:{config['server']['port']}")
    uvicorn.run(
        app,
        host=config['server']['host'],
        port=config['server']['port']
    )
