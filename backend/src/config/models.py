"""Configuration models with Pydantic validation."""
from pydantic import BaseModel, Field
from typing import Optional, List


class BedrockConfig(BaseModel):
    """AWS Bedrock configuration."""
    region: str = "us-east-1"
    model_id: str


class GrokConfig(BaseModel):
    """Grok API configuration."""
    enabled: bool = True
    api_key: str
    base_url: str = "https://api.x.ai/v1"
    model: str = "grok-beta"
    max_tokens: int = 1000


class EmbeddingsConfig(BaseModel):
    """Embeddings configuration."""
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_method: str = Field(default="semantic", pattern="^(semantic|fixed)$")
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    semantic_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    max_chunk_size: int = Field(default=1000, ge=100)
    min_chunk_size: int = Field(default=100, ge=50)


class FAISSConfig(BaseModel):
    """FAISS vector search configuration."""
    index_path: str = "../faiss_index"
    top_k: int = Field(default=10, ge=1, le=100)
    distance_threshold: Optional[float] = Field(default=1.5, ge=0.0)
    persist_index: bool = True
    index_file: str = "../faiss_index/index.faiss"
    metadata_file: str = "../faiss_index/metadata.json"


class RerankerConfig(BaseModel):
    """Reranker configuration."""
    enabled: bool = True
    method: str = Field(default="hybrid", pattern="^(cross-encoder|bm25|hybrid|mmr)$")
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k: int = Field(default=3, ge=1, le=20)
    score_threshold: Optional[float] = Field(default=0.3, ge=0.0, le=1.0)
    ce_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    bm25_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    mmr_lambda: float = Field(default=0.7, ge=0.0, le=1.0)


class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1024, le=65535)
    reload: bool = False


class RedisConfig(BaseModel):
    """Redis cache configuration."""
    host: str = "localhost"
    port: int = Field(default=6379, ge=1024, le=65535)
    db: int = Field(default=0, ge=0)
    socket_timeout: int = Field(default=2, ge=1)


class WebSearchConfig(BaseModel):
    """Web search configuration."""
    vlm_enabled: bool = True
    vlm_model: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    vlm_use_bedrock: bool = True
    vlm_region: str = "us-west-2"
    api_discovery_enabled: bool = True
    js_rendering_enabled: bool = True
    llm_judge_enabled: bool = True
    llm_judge_model: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    min_request_interval: float = Field(default=0.5, ge=0.0)
    cache_ttl: int = Field(default=300, ge=0)


class ApplicationConfig(BaseModel):
    """Application-level configuration."""
    max_history_messages: int = Field(default=6, ge=1)
    max_content_preview: int = Field(default=200, ge=50)
    max_doc_context_length: int = Field(default=300, ge=100)
    query_rate_limit: int = Field(default=120, ge=1)
    default_search_limit: int = Field(default=10, ge=1)
    max_search_results: int = Field(default=20, ge=1)
    cache_ttl_seconds: int = Field(default=3600, ge=0)
    web_cache_ttl: int = Field(default=1800, ge=0)
    rag_cache_ttl: int = Field(default=3600, ge=0)
    web_search_timeout: int = Field(default=5, ge=1)
    rag_search_timeout: int = Field(default=3, ge=1)
    llm_timeout: int = Field(default=30, ge=1)
    suggestion_limit: int = Field(default=5, ge=1)
    min_query_length_for_suggestions: int = Field(default=2, ge=1)
    cot_min_word_count: int = Field(default=10, ge=1)
    cot_intents: List[str] = Field(default=['factual', 'how_to'])


class RAGConfig(BaseModel):
    """Complete RAG system configuration."""
    bedrock: BedrockConfig
    grok: GrokConfig
    embeddings: EmbeddingsConfig
    faiss: FAISSConfig
    reranker: RerankerConfig
    server: ServerConfig
    redis: RedisConfig
    web_search: WebSearchConfig
    application: ApplicationConfig
