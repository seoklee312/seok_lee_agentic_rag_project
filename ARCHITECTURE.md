# Framework Architecture

## Overview

Clean architecture implementation with clear separation of concerns, following SOLID principles and dependency inversion.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                  │
│                  routers/domain.py                      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Application Layer                      │
│              evaluation/evaluator.py                    │
│              orchestration/agentic.py                   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Domain Layer                         │
│         domains/base.py (Abstract Interface)            │
│         domains/medical/, domains/legal/                │
│         domains/tools.py (Tool Registry)                │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                Infrastructure Layer                     │
│    services/grok_client.py (Grok API)                   │
│    services/xai_collections.py (Collections API)        │
│    services/faiss_rag.py (Vector Store)                 │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              Cross-Cutting Concerns                     │
│    utils/errors.py (Error Classification)               │
│    utils/tracing.py (Request Tracing)                   │
│    config/ (Configuration)                              │
└─────────────────────────────────────────────────────────┘
```

---

## 1. Config-Driven Domain Switching ✅

### YAML Configuration
```yaml
# backend/src/domains/medical/config.yaml
domain:
  name: medical
  description: Healthcare and clinical decision support
  system_prompt: |
    You are a medical AI assistant...
  sample_documents:
    - title: "Aspirin Guidelines"
      content: "..."
```

### Dynamic Loading
```python
# domains/manager.py
class DomainManager:
    def switch_domain(self, domain_name: str) -> BaseDomain:
        """Load domain dynamically from config"""
        config = self._load_config(domain_name)
        domain_class = self._get_domain_class(domain_name)
        return domain_class(config)
```

### Features
- ✅ YAML-based configuration
- ✅ Dynamic prompt loading
- ✅ Dynamic tool loading
- ✅ Dynamic data source loading
- ✅ Hot-swappable domains

---

## 2. Clear Abstraction Layers ✅

### Domain Layer (Core Business Logic)
```python
# domains/base.py
class BaseDomain(ABC):
    @abstractmethod
    def get_system_prompt(self) -> str: pass
    
    @abstractmethod
    def get_tools(self) -> ToolRegistry: pass
    
    @abstractmethod
    def preprocess_query(self, query: str) -> str: pass
    
    @abstractmethod
    def postprocess_response(self, response: str) -> str: pass
```

**Implementations:**
- `domains/medical/domain.py` - Medical domain
- `domains/legal/domain.py` - Legal domain

### Tools Layer
```python
# domains/tools.py
class BaseTool(ABC):
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]: pass

class ToolRegistry:
    def register(self, tool: BaseTool): pass
    def execute(self, name: str, **kwargs): pass
```

### Services Layer (Infrastructure Adapters)
- `services/grok_client.py` - Grok API client
- `services/xai_collections.py` - Collections API
- `services/faiss_rag.py` - Vector store

### Utilities Layer (Cross-Cutting)
- `utils/errors.py` - Error classification
- `utils/tracing.py` - Request tracing
- `config/` - Configuration management

---

## 3. Reusable Grok API Client ✅

### Features

**Authentication**
```python
headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Content-Type": "application/json"
}
```

**Retry with Exponential Backoff**
```python
for attempt in range(self.max_retries):
    try:
        return await self._make_request(...)
    except Exception as e:
        delay = self.retry_delay * (2 ** attempt)
        await asyncio.sleep(delay)
```

**Rate Limiting (Token Bucket)**
```python
class RateLimiter:
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.requests = deque()
    
    async def acquire(self):
        # Wait if rate limit exceeded
```

**Fallback Mechanism**
```python
try:
    return await self.grok_client.chat_completion(...)
except Exception:
    if self.bedrock_fallback:
        return await self.bedrock_fallback.generate(...)
```

**Metrics Tracking**
```python
self.total_requests += 1
self.successful_requests += 1
self.failed_requests += 1
```

---

## 4. Centralized Utilities ✅

### Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Domain switched to: medical")
logger.error(f"Query failed: {e}", exc_info=True)
```

### Tracing (Correlation IDs)
```python
# utils/tracing.py
class Tracer:
    @staticmethod
    def start_trace(operation: str) -> TraceContext:
        trace_id = str(uuid.uuid4())
        return TraceContext(trace_id, operation)
    
    @staticmethod
    def end_trace(ctx: TraceContext, status: str):
        duration = time.time() - ctx.start_time
        logger.info(f"Trace {ctx.trace_id}: {status} ({duration:.3f}s)")
```

### Error Classification
```python
# utils/errors.py
class FrameworkError(Exception):
    """Base framework error"""

class DomainError(FrameworkError):
    """Domain-specific errors"""

class APIError(FrameworkError):
    """External API errors"""

class ConfigError(FrameworkError):
    """Configuration errors"""
```

---

## Dependency Flow

```
Outer Layers → Inner Layers (Dependency Inversion)

routers/domain.py
    ↓ depends on
evaluation/evaluator.py
    ↓ depends on
domains/base.py (Interface)
    ↑ implemented by
domains/medical/domain.py
    ↓ uses
services/grok_client.py
    ↓ uses
utils/errors.py, utils/tracing.py
```

**Key Principle:** Dependencies point inward. Inner layers (domain) don't know about outer layers (API).

---

## SOLID Principles

✅ **Single Responsibility** - Each class has one reason to change  
✅ **Open/Closed** - Open for extension (new domains), closed for modification  
✅ **Liskov Substitution** - BaseDomain implementations are interchangeable  
✅ **Interface Segregation** - Small, focused interfaces (BaseDomain, BaseTool)  
✅ **Dependency Inversion** - Depend on abstractions (BaseDomain), not concretions  

---

## Testing Strategy

```python
# Unit Tests
test_domains.py          # Domain logic
test_tools.py            # Tool execution
test_metrics.py          # Metrics calculation

# RAG Store Management
rag_store_reset.py       # Reset xAI Collections + FAISS
rag_store_add_news.py    # Add domain-specific news
```

---

## Configuration Management

```
backend/config.yaml              # Global config
backend/src/domains/medical/config.yaml   # Domain config
backend/src/domains/legal/config.yaml     # Domain config
.env                             # Secrets (API keys)
```

**Separation:**
- Global config: Models, rate limits, timeouts
- Domain config: Prompts, tools, sample data
- Secrets: API keys (never committed)

---

## Framework Verification

```bash
✅ Config-driven domain switching
   - Medical domain loaded: medical
   - Tools: ['drug_interaction_checker', 'symptom_analyzer']

✅ Clear abstraction layers
   - Domain Layer: BaseDomain → Medical/Legal
   - Tools Layer: BaseTool → Domain-specific tools
   - Services Layer: GrokClient, Collections, FAISS
   - Utils Layer: Logging, Tracing, Errors

✅ Reusable Grok API client
   - Authentication: ✓
   - Retry logic: ✓ (exponential backoff)
   - Rate limiting: ✓ (60 req/min)
   - Fallback: ✓ (Bedrock)

✅ Centralized utilities
   - Logging: ✓ (Python logging)
   - Tracing: ✓ (correlation IDs)
   - Error classification: ✓ (FrameworkError hierarchy)
```

---

## Summary

**Clean Architecture:** ✅  
**SOLID Principles:** ✅  
**Framework Requirements:** ✅  
**Production Ready:** ✅
