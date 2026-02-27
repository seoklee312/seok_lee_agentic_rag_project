# 🚀 Deployment Guide

## Quick Start (Docker)

### Prerequisites
- Docker Desktop installed
- xAI API key

### Deploy in 2 Steps

**1. Configure**
```bash
# Edit .env file
XAI_API_KEY=your_key_here
```

**2. Start**
```bash
./start.sh
```

**Access:** http://localhost:8000

---

## Docker Deployment

### Build and Start
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

### Stop
```bash
# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

## Manual Deployment (Without Docker)

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Create .env file
cat > .env << EOF
XAI_API_KEY=your_key_here
REDIS_HOST=localhost
REDIS_PORT=6379
EOF
```

### 3. Start Redis (Optional)
```bash
# Mac
brew install redis
redis-server

# Linux
sudo apt-get install redis-server
sudo systemctl start redis
```

### 4. Start Application
```bash
cd backend/src
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

---

## Production Deployment

### Environment Variables

```bash
# Required
XAI_API_KEY=your_key_here

# Optional
REDIS_HOST=localhost
REDIS_PORT=6379
LOG_LEVEL=INFO
MAX_WORKERS=4
```

### Configuration

```yaml
# backend/config.yaml
grok:
  models:
    default: grok-3-mini      # Development
    production: grok-4-latest  # Production
  max_tokens: 4096
  rate_limit: 60
  timeout: 30

redis:
  host: ${REDIS_HOST}
  port: ${REDIS_PORT}
  ttl: 3600

application:
  use_agentic_workflow: true
  thread_pool_size: 32
```

### Scaling

**Horizontal Scaling:**
```bash
# Scale app instances
docker-compose up -d --scale app=3
```

**Load Balancer:**
```nginx
upstream grok_demo {
    server app1:8000;
    server app2:8000;
    server app3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://grok_demo;
    }
}
```

---

## Health Checks

### Application Health
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

### Redis Health
```bash
docker-compose exec redis redis-cli ping
# Expected: PONG
```

### System Metrics
```bash
curl http://localhost:8000/v1/system/metrics
```

---

## Monitoring

### Logs
```bash
# Application logs
docker-compose logs -f app

# Redis logs
docker-compose logs -f redis

# All logs
docker-compose logs -f
```

### Metrics
- **Endpoint:** http://localhost:8000/v1/system/metrics
- **Metrics:** Queries, latency, cache hits, errors

---

## Backup and Recovery

### Backup FAISS Index
```bash
# Backup
docker cp grok-demo-app:/app/backend/data ./backup/

# Restore
docker cp ./backup/data grok-demo-app:/app/backend/
```

### Backup Redis
```bash
# Backup
docker-compose exec redis redis-cli SAVE
docker cp grok-demo-redis:/data/dump.rdb ./backup/

# Restore
docker cp ./backup/dump.rdb grok-demo-redis:/data/
docker-compose restart redis
```

---

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs app

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

### Port Already in Use
```bash
# Find process
lsof -i :8000

# Change port in docker-compose.yml
ports:
  - "8001:8000"
```

### Out of Memory
```bash
# Increase Docker memory
# Docker Desktop → Settings → Resources → Memory

# Or reduce workers
# In config.yaml:
application:
  thread_pool_size: 16
```

---

## Security

### API Key Protection
```bash
# Never commit .env
echo ".env" >> .gitignore

# Use secrets management in production
# AWS Secrets Manager, HashiCorp Vault, etc.
```

### Network Security
```bash
# Restrict access
# In docker-compose.yml:
ports:
  - "127.0.0.1:8000:8000"  # Localhost only
```

---

## Updates

### Update Application
```bash
# Pull latest code
git pull

# Rebuild
docker-compose build

# Restart
docker-compose up -d
```

### Update Dependencies
```bash
# Update requirements.txt
pip install --upgrade -r backend/requirements.txt

# Rebuild
docker-compose build --no-cache
```

---

## Performance Tuning

### Redis Optimization
```bash
# In docker-compose.yml:
redis:
  command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

### Application Optimization
```yaml
# In config.yaml:
application:
  thread_pool_size: 32  # Adjust based on CPU cores
  use_agentic_workflow: true
  
redis:
  ttl: 3600  # Cache TTL in seconds
```

---

## Cost Optimization

### Use Cheaper Models
```yaml
# In config.yaml:
grok:
  models:
    default: grok-3-mini  # $0.0005/request
```

### Enable Caching
```yaml
# In config.yaml:
redis:
  enabled: true
  ttl: 3600  # 1 hour cache
```

### Monitor Usage
```bash
# Check metrics
curl http://localhost:8000/v1/system/metrics

# Look for:
# - cache_hits (higher is better)
# - total_queries (monitor costs)
```

---

## Production Checklist

- [ ] Environment variables configured
- [ ] Redis running and accessible
- [ ] Health checks passing
- [ ] Logs configured
- [ ] Monitoring enabled
- [ ] Backups scheduled
- [ ] Security hardened
- [ ] Load testing completed
- [ ] Documentation updated
- [ ] Team trained

---

## Support

**Issues:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)  
**Architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md)  
**Usage:** See [README.md](README.md)
