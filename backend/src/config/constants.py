"""Configuration constants for the application."""
import yaml
import os
import re
from pathlib import Path

def _expand_env_vars(config):
    """Recursively expand ${VAR} in config values."""
    if isinstance(config, dict):
        return {k: _expand_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_expand_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Replace ${VAR} with environment variable value
        return re.sub(r'\$\{(\w+)\}', lambda m: os.getenv(m.group(1), m.group(0)), config)
    return config

# Load config
config_path = Path(__file__).parent.parent.parent / 'config.yaml'
with open(config_path, 'r') as f:
    _config = yaml.safe_load(f)

# Expand environment variables
_config = _expand_env_vars(_config)

_app_config = _config.get('application', {})

# Query processing
MAX_HISTORY_MESSAGES = _app_config.get('max_history_messages', 6)
MAX_CONTENT_PREVIEW = _app_config.get('max_content_preview', 200)
MAX_DOC_CONTEXT_LENGTH = _app_config.get('max_doc_context_length', 300)

# Rate limiting
QUERY_RATE_LIMIT = _app_config.get('query_rate_limit', 120)

# Search
DEFAULT_SEARCH_LIMIT = _app_config.get('default_search_limit', 10)
MAX_SEARCH_RESULTS = _app_config.get('max_search_results', 20)

# Caching
CACHE_TTL_SECONDS = _app_config.get('cache_ttl_seconds', 3600)
WEB_CACHE_TTL = _app_config.get('web_cache_ttl', 1800)
RAG_CACHE_TTL = _app_config.get('rag_cache_ttl', 3600)

# Timeouts
WEB_SEARCH_TIMEOUT = _app_config.get('web_search_timeout', 5)
RAG_SEARCH_TIMEOUT = _app_config.get('rag_search_timeout', 3)
LLM_TIMEOUT = _app_config.get('llm_timeout', 30)

# Suggestions
SUGGESTION_LIMIT = _app_config.get('suggestion_limit', 5)
MIN_QUERY_LENGTH_FOR_SUGGESTIONS = _app_config.get('min_query_length_for_suggestions', 2)

# Auto-detection thresholds
COT_MIN_WORD_COUNT = _app_config.get('cot_min_word_count', 10)
COT_INTENTS = _app_config.get('cot_intents', ['factual', 'how_to'])
