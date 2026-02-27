"""Services package - organized by domain."""

# Query services
from .query import (
    QueryService,
    QueryOptimizer,
    query_optimizer,
    QueryPreprocessor,
    QuerySuggestionsService,
    TemporalFilter,
)

# Web search services
from .web_search import (
    WebSearchService,
)

# LLM services
from .llm import (
    LLMService,
    BedrockService,
    GrokService,
    PromptBuilder,
    prompt_builder,
)

# Cache services
from .cache import (
    CacheService,
    cache_service,
    SemanticCache,
)

# FAISS services
from .faiss import (
    DocumentIngestionService,
    DocumentManager,
    VectorSearchService,
    FaissRAGEngine,
)

# Feedback services
from .feedback import (
    FeedbackCollector,
)

# State services
from .state import (
    MemoryManager,
)

# Validation services
from .validation import (
    HallucinationDetector,
)

# Monitoring services
from .monitoring import (
    MetricsService,
    metrics_service,
)

__all__ = [
    # Query
    'QueryService',
    'QueryOptimizer',
    'query_optimizer',
    'QueryPreprocessor',
    'QuerySuggestionsService',
    'TemporalFilter',
    # Web search
    'WebSearchService',
    # LLM
    'LLMService',
    'BedrockService',
    'GrokService',
    'PromptBuilder',
    'prompt_builder',
    # Cache
    'CacheService',
    'cache_service',
    'SemanticCache',
    # FAISS
    'DocumentIngestionService',
    'DocumentManager',
    'VectorSearchService',
    'FaissRAGEngine',
    # Feedback
    'FeedbackCollector',
    # State
    'MemoryManager',
    # Validation
    'HallucinationDetector',
    # Monitoring
    'MetricsService',
    'metrics_service',
]
