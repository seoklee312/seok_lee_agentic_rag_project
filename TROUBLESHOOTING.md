# 🔧 Troubleshooting Guide

## Common Issues

### 1. Container Won't Start

**Symptom:** `docker-compose up` fails

**Solutions:**
```bash
# Check logs
docker-compose logs app

# Common causes:
# - Port 8000 already in use
lsof -i :8000
kill -9 <PID>

# - Missing .env file
cp .env.example .env
# Edit XAI_API_KEY

# - Docker out of memory
# Docker Desktop → Settings → Resources → Increase Memory

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

### 2. API Key Errors

**Symptom:** `401 Unauthorized` or `Invalid API key`

**Solutions:**
```bash
# Check .env file exists
cat .env

# Verify key format
# Should start with: xai-...

# Get new key from: console.x.ai

# Restart after updating
docker-compose restart app
```

---

### 3. Redis Connection Failed

**Symptom:** `Connection refused` or `Redis unavailable`

**Solutions:**
```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
# Expected: PONG

# Restart Redis
docker-compose restart redis

# Check Redis logs
docker-compose logs redis

# If still failing, disable Redis:
# In config.yaml:
redis:
  enabled: false
```

---

### 4. Slow Response Times

**Symptom:** Queries take >10 seconds

**Solutions:**
```bash
# Check cache hit rate
curl http://localhost:8000/v1/system/metrics

# Enable caching if disabled
# In config.yaml:
redis:
  enabled: true
  ttl: 3600

# Use faster model
# In config.yaml:
grok:
  models:
    default: grok-3-mini  # Faster than grok-4-latest

# Reduce max_tokens
grok:
  max_tokens: 2048  # Down from 4096

# Check network latency
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
```

---

### 5. Domain Detection Not Working

**Symptom:** Queries not auto-routed to correct domain

**Solutions:**
```bash
# Check domain detector initialized
curl http://localhost:8000/v1/system/config

# Test detection manually
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are aspirin side effects?", "debug": true}'

# Check logs for detection
docker-compose logs app | grep "Domain detected"

# Fallback to manual domain selection
curl -X POST http://localhost:8000/v1/domain/switch \
  -H "Content-Type: application/json" \
  -d '{"domain": "medical"}'
```

---

### 6. Out of Memory

**Symptom:** Container crashes or `MemoryError`

**Solutions:**
```bash
# Increase Docker memory
# Docker Desktop → Settings → Resources → Memory (8GB+)

# Reduce thread pool size
# In config.yaml:
application:
  thread_pool_size: 16  # Down from 32

# Clear FAISS index
rm -rf backend/data/faiss_index

# Restart with clean state
docker-compose down -v
docker-compose up -d
```

---

### 7. Import Errors

**Symptom:** `ModuleNotFoundError` or `ImportError`

**Solutions:**
```bash
# Rebuild container
docker-compose build --no-cache

# Check requirements installed
docker-compose exec app pip list

# Install missing packages
docker-compose exec app pip install <package>

# Or add to requirements.txt and rebuild
```

---

### 8. FAISS Index Errors

**Symptom:** `IndexError` or `FAISS not initialized`

**Solutions:**
```bash
# Rebuild index
docker-compose exec app python -c "
from services.rag_service import RAGService
rag = RAGService()
rag.rebuild_index()
"

# Or delete and restart
rm -rf backend/data/faiss_index
docker-compose restart app
```

---

### 9. Rate Limit Exceeded

**Symptom:** `429 Too Many Requests`

**Solutions:**
```bash
# Check rate limit config
# In config.yaml:
grok:
  rate_limit: 60  # Requests per minute

# Enable caching to reduce API calls
redis:
  enabled: true
```

---

### 10. Health Check Failing

**Symptom:** `/health` returns error

**Solutions:**
```bash
# Check app logs
docker-compose logs app

# Test components individually
curl http://localhost:8000/v1/system/config
curl http://localhost:8000/v1/domain/list

# Restart app
docker-compose restart app

# Check dependencies
docker-compose exec app python -c "
import sys
sys.path.insert(0, '/app/backend/src')
from app import app
print('App loaded successfully')
"
```

---

## Debug Mode

### Enable Verbose Logging
```bash
# In .env:
LOG_LEVEL=DEBUG

# Restart
docker-compose restart app

# View logs
docker-compose logs -f app
```

### Test Individual Components
```bash
# Test Grok client
docker-compose exec app python test_grok_integration.py

# Test via API
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are aspirin contraindications?"}'
```

---

## Error Messages

### "Domain not found"
```bash
# List available domains
curl http://localhost:8000/v1/domain/list

# Check domain config exists
ls backend/src/domains/*/config.yaml
```

### "Collection not found"
```bash
# Collections API may be disabled
# Check config.yaml:
xai_collections:
  enabled: false  # Set to true if needed
```

### "Timeout waiting for response"
```bash
# Increase timeout
# In config.yaml:
grok:
  timeout: 60  # Up from 30
```

---

## Performance Issues

### High Latency
```bash
# Check metrics
curl http://localhost:8000/v1/system/metrics

# Optimize:
# 1. Enable caching
# 2. Use grok-3-mini
# 3. Reduce max_tokens
# 4. Increase thread_pool_size
```

### High Memory Usage
```bash
# Check memory
docker stats grok-demo-app

# Optimize:
# 1. Reduce thread_pool_size
# 2. Clear FAISS index
# 3. Disable unused domains
# 4. Reduce Redis TTL
```

---

## Getting Help

### Collect Debug Info
```bash
# System info
docker-compose version
docker version

# App logs
docker-compose logs app > app.log

# Config
cat backend/config.yaml

# Metrics
curl http://localhost:8000/v1/system/metrics > metrics.json
```

### Check Documentation
- [README.md](README.md) - Usage guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [RAG_FEATURES.md](RAG_FEATURES.md) - RAG configuration

---

## FAQ

**Q: Can I run without Docker?**  
A: Yes, see [DEPLOYMENT.md](DEPLOYMENT.md) manual deployment section.

**Q: Can I run without Redis?**  
A: Yes, set `redis.enabled: false` in config.yaml. Caching will be disabled.

**Q: How do I add a new domain?**  
A: See [README.md](README.md) "Adding New Domains" section.

**Q: How do I change the model?**  
A: Edit `grok.models.default` in config.yaml and restart.

**Q: How do I reduce costs?**  
A: Use grok-3-mini, enable caching, reduce max_tokens.

**Q: How do I improve accuracy?**  
A: Use grok-4-latest, increase max_tokens, add more documents.

---

## Still Stuck?

1. Check logs: `docker-compose logs -f app`
2. Test health: `curl http://localhost:8000/health`
3. Rebuild: `docker-compose build --no-cache`
4. Clean start: `docker-compose down -v && docker-compose up -d`
5. Review docs: [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md)
