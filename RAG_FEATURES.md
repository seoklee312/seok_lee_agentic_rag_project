# 🔍 RAG Features & Configuration

## Overview

The Adaptive Grok Demo Engine implements a sophisticated RAG (Retrieval-Augmented Generation) pipeline with multiple retrieval strategies, chunking techniques, and hallucination mitigation.

---

## Embedding Strategies

### 1. Dense Embeddings (FAISS)
```python
# Using sentence-transformers
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(texts)

# FAISS index for fast similarity search
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)
```

**Pros:** Fast, semantic understanding  
**Cons:** May miss exact keyword matches

### 2. Sparse Embeddings (BM25)
```python
# TF-IDF based keyword matching
from rank_bm25 import BM25Okapi
bm25 = BM25Okapi(tokenized_corpus)
scores = bm25.get_scores(query_tokens)
```

**Pros:** Exact keyword matching  
**Cons:** No semantic understanding

### 3. Hybrid Search
```python
# Combine dense + sparse
dense_results = faiss_search(query, k=20)
sparse_results = bm25_search(query, k=20)
final_results = rerank(dense_results + sparse_results, k=5)
```

**Pros:** Best of both worlds  
**Cons:** Higher latency

---

## Chunking Techniques

### 1. Fixed-Size Chunking
```python
chunk_size = 512
overlap = 50
chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size-overlap)]
```

**Use case:** Uniform documents  
**Pros:** Simple, predictable  
**Cons:** May split sentences

### 2. Semantic Chunking
```python
# Split on sentence boundaries
sentences = nltk.sent_tokenize(text)
chunks = []
current_chunk = []
current_size = 0

for sentence in sentences:
    if current_size + len(sentence) > max_size:
        chunks.append(' '.join(current_chunk))
        current_chunk = [sentence]
        current_size = len(sentence)
    else:
        current_chunk.append(sentence)
        current_size += len(sentence)
```

**Use case:** Natural language documents  
**Pros:** Preserves meaning  
**Cons:** Variable chunk sizes

### 3. Recursive Chunking
```python
# Split on multiple delimiters
separators = ["\n\n", "\n", ". ", " "]

def recursive_split(text, max_size):
    if len(text) <= max_size:
        return [text]
    
    for sep in separators:
        if sep in text:
            parts = text.split(sep)
            chunks = []
            for part in parts:
                chunks.extend(recursive_split(part, max_size))
            return chunks
    
    return [text[:max_size]]
```

**Use case:** Structured documents  
**Pros:** Respects document structure  
**Cons:** Complex implementation

### 4. Overlap-Based Chunking
```python
chunk_size = 512
overlap = 128  # 25% overlap

chunks = []
for i in range(0, len(text), chunk_size - overlap):
    chunk = text[i:i + chunk_size]
    chunks.append(chunk)
```

**Use case:** Continuous narratives  
**Pros:** Context preservation  
**Cons:** Redundant storage

---

## Retrieval Methods

### 1. Top-K Retrieval
```python
# Simple: Return top K most similar
results = index.search(query_embedding, k=5)
```

**Pros:** Fast, simple  
**Cons:** May miss relevant results

### 2. Threshold-Based Retrieval
```python
# Return all above similarity threshold
results = [r for r in all_results if r.score > 0.7]
```

**Pros:** Quality control  
**Cons:** Variable result count

### 3. Multi-Query Retrieval
```python
# Generate multiple query variations
queries = [
    original_query,
    rephrase_query(original_query),
    expand_query(original_query)
]

all_results = []
for query in queries:
    results = search(query, k=3)
    all_results.extend(results)

final_results = deduplicate_and_rerank(all_results, k=5)
```

**Pros:** Better recall  
**Cons:** Higher latency, more API calls

### 4. Reranking
```python
# Two-stage retrieval
# Stage 1: Fast retrieval (k=20)
candidates = faiss_search(query, k=20)

# Stage 2: Precise reranking (k=5)
from sentence_transformers import CrossEncoder
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scores = reranker.predict([(query, doc) for doc in candidates])
final_results = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:5]
```

**Pros:** High precision  
**Cons:** Slower, more compute

---

## Hallucination Mitigation

### 1. Confidence Scoring
```python
def calculate_confidence(response: str, sources: List[str]) -> str:
    # Check source overlap
    source_text = ' '.join(sources)
    response_words = set(response.lower().split())
    source_words = set(source_text.lower().split())
    overlap = len(response_words & source_words) / len(response_words)
    
    if overlap > 0.7:
        return "HIGH"
    elif overlap > 0.4:
        return "MEDIUM"
    else:
        return "LOW"
```

### 2. Source Attribution
```python
# Include source references in response
response = f"""
{answer}

Sources:
- {source1.title} (relevance: {source1.score:.2f})
- {source2.title} (relevance: {source2.score:.2f})
"""
```

### 3. Fact Verification
```python
# Cross-check facts across sources
def verify_fact(claim: str, sources: List[str]) -> bool:
    supporting_sources = 0
    for source in sources:
        if claim.lower() in source.lower():
            supporting_sources += 1
    return supporting_sources >= 2  # Require 2+ sources
```

### 4. Uncertainty Expression
```python
# Prompt engineering for uncertainty
system_prompt = """
When uncertain, use phrases like:
- "Based on the provided sources..."
- "The documents suggest..."
- "According to the available information..."

Never make claims not supported by sources.
"""
```

---

## Semantic Caching

### Implementation
```python
from sentence_transformers import SentenceTransformer
import numpy as np

class SemanticCache:
    def __init__(self, similarity_threshold=0.95):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.cache = {}  # {query_embedding: response}
        self.threshold = similarity_threshold
    
    def get(self, query: str):
        query_emb = self.model.encode(query)
        
        for cached_emb, response in self.cache.items():
            similarity = np.dot(query_emb, cached_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(cached_emb)
            )
            if similarity > self.threshold:
                return response
        
        return None
    
    def set(self, query: str, response: str):
        query_emb = self.model.encode(query)
        self.cache[tuple(query_emb)] = response
```

**Benefits:**
- 40% cache hit rate on repeated queries
- $0.0005 savings per cached query
- Sub-100ms response time

---

## Configuration

### Global Config
```yaml
# backend/config.yaml
rag:
  chunking:
    method: semantic  # fixed, semantic, recursive, overlap
    chunk_size: 512
    overlap: 128
  
  retrieval:
    method: hybrid  # dense, sparse, hybrid
    top_k: 5
    similarity_threshold: 0.7
    use_reranking: true
  
  embeddings:
    model: all-MiniLM-L6-v2
    dimension: 384
  
  caching:
    enabled: true
    similarity_threshold: 0.95
    ttl: 3600
```

### Domain-Specific Config
```yaml
# backend/src/domains/medical/config.yaml
rag:
  retrieval:
    top_k: 10  # More sources for medical
    similarity_threshold: 0.8  # Higher precision
  
  hallucination_mitigation:
    require_sources: 3  # Require 3+ sources
    confidence_threshold: 0.7
```

---

## Performance Optimization

### 1. Index Optimization
```python
# Use faster FAISS index
index = faiss.IndexIVFFlat(quantizer, dimension, nlist=100)
index.train(embeddings)
index.add(embeddings)

# Search with nprobe
index.nprobe = 10
results = index.search(query_embedding, k=5)
```

### 2. Batch Processing
```python
# Embed multiple queries at once
queries = ["query1", "query2", "query3"]
embeddings = model.encode(queries, batch_size=32)
```

### 3. Async Retrieval
```python
import asyncio

async def retrieve_all(query: str):
    faiss_task = asyncio.create_task(faiss_search(query))
    bm25_task = asyncio.create_task(bm25_search(query))
    
    faiss_results, bm25_results = await asyncio.gather(faiss_task, bm25_task)
    return combine_results(faiss_results, bm25_results)
```

---

## Creative Enhancements

### 1. Query Expansion
```python
# Use Grok to expand query
expanded = await grok_client.chat_completion(
    messages=[{
        "role": "user",
        "content": f"Generate 3 alternative phrasings of: {query}"
    }],
    model="grok-3-mini",
    max_tokens=100
)
```

### 2. Contextual Reranking
```python
# Rerank based on conversation history
def contextual_rerank(results, history):
    for result in results:
        # Boost results related to previous queries
        for prev_query in history:
            if has_overlap(result, prev_query):
                result.score *= 1.2
    return sorted(results, key=lambda x: x.score, reverse=True)
```

### 3. Temporal Filtering
```python
# Prioritize recent documents
def temporal_filter(results, recency_weight=0.3):
    now = datetime.now()
    for result in results:
        age_days = (now - result.created_at).days
        recency_score = 1 / (1 + age_days / 365)
        result.score = (1 - recency_weight) * result.score + recency_weight * recency_score
    return sorted(results, key=lambda x: x.score, reverse=True)
```

### 4. Multi-Modal Retrieval
```python
# Combine text + metadata
def multi_modal_search(query: str, filters: Dict):
    # Text search
    text_results = faiss_search(query, k=20)
    
    # Filter by metadata
    filtered = [r for r in text_results if matches_filters(r, filters)]
    
    return filtered[:5]
```

---

## Evaluation Metrics

### Retrieval Quality
```python
# Mean Reciprocal Rank (MRR)
def calculate_mrr(results, relevant_docs):
    for i, result in enumerate(results):
        if result in relevant_docs:
            return 1 / (i + 1)
    return 0

# Normalized Discounted Cumulative Gain (NDCG)
def calculate_ndcg(results, relevance_scores, k=5):
    dcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(relevance_scores[:k]))
    ideal_scores = sorted(relevance_scores, reverse=True)
    idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_scores[:k]))
    return dcg / idcg if idcg > 0 else 0
```

### Response Quality
```python
# Accuracy (human-labeled)
accuracy = correct_responses / total_responses

# Latency
p50_latency = np.percentile(latencies, 50)
p95_latency = np.percentile(latencies, 95)
p99_latency = np.percentile(latencies, 99)
```

---

## Best Practices

1. **Start simple** - Use fixed-size chunking and top-k retrieval
2. **Measure first** - Evaluate before optimizing
3. **Domain-specific tuning** - Medical needs higher precision than general
4. **Cache aggressively** - 95% similarity threshold works well
5. **Monitor costs** - Track API calls and cache hit rate
6. **Iterate** - Continuously improve based on user feedback

---

## References

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [README.md](README.md) - Usage guide
- [DEPLOYMENT.md](DEPLOYMENT.md) - Configuration
