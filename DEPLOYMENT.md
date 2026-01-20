# Deployment Guide

This guide covers deploying the Minecraft MOTD Embed API to production.

## Pre-Deployment Checklist

Before deploying to production, ensure you've addressed these items:

### Security
- [ ] Set `ALLOWED_ORIGINS` to specific domains (not `*`)
- [ ] Review and implement rate limiting if needed
- [ ] Consider SSRF protection (IP allowlisting/denylisting)
- [ ] Ensure `RELOAD=false` in production
- [ ] Set `LOG_LEVEL` appropriately (info or warning)
- [ ] Review CORS settings for your use case

### Infrastructure
- [ ] Set up health check monitoring
- [ ] Configure log aggregation
- [ ] Set up container restart policies
- [ ] Configure resource limits (CPU/Memory)
- [ ] Set up SSL/TLS termination (e.g., reverse proxy)

### Testing
- [ ] Test with various Minecraft servers
- [ ] Verify caching behavior
- [ ] Test error handling (offline servers, invalid IPs)
- [ ] Load testing (if expecting high traffic)

## Docker Deployment

### Quick Deploy with Docker Compose

1. **Clone and configure**
   ```bash
   git clone <repository-url>
   cd motd-embed-api
   cp .env.example .env
   ```

2. **Edit `.env` with production settings**
   ```env
   HOST=0.0.0.0
   PORT=8000
   RELOAD=false
   LOG_LEVEL=info
   ALLOWED_ORIGINS=https://example.com,https://app.example.com
   ```

3. **Deploy**
   ```bash
   docker-compose up -d
   ```

4. **Verify deployment**
   ```bash
   # Check container status
   docker-compose ps

   # Check logs
   docker-compose logs -f

   # Test health endpoint
   curl http://localhost:8000/health
   ```

### Manual Docker Deployment

```bash
# Build
docker build -t motd-embed-api:v1.0.0 .

# Run
docker run -d \
  --name motd-embed-api \
  -p 8000:8000 \
  -e ALLOWED_ORIGINS="https://example.com" \
  -e LOG_LEVEL="info" \
  --restart unless-stopped \
  motd-embed-api:v1.0.0

# View logs
docker logs -f motd-embed-api
```

## Reverse Proxy Setup

### Nginx

```nginx
upstream motd_api {
    server localhost:8000;
}

server {
    listen 80;
    server_name api.example.com;

    # Redirect to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://motd_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static/ {
        proxy_pass http://motd_api/static/;
        proxy_cache_valid 200 1d;
        add_header Cache-Control "public, max-age=86400";
    }
}
```

### Traefik (Docker Labels)

Add to `docker-compose.yml`:

```yaml
services:
  api:
    # ... existing config ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.motd-api.rule=Host(`api.example.com`)"
      - "traefik.http.routers.motd-api.entrypoints=websecure"
      - "traefik.http.routers.motd-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.motd-api.loadbalancer.server.port=8000"
```

## Kubernetes Deployment

See `README.md` for full Kubernetes manifests. Quick deploy:

```bash
# Create namespace
kubectl create namespace motd-api

# Create config
kubectl create configmap motd-api-config \
  --from-literal=ALLOWED_ORIGINS=https://example.com \
  --from-literal=LOG_LEVEL=info \
  -n motd-api

# Deploy
kubectl apply -f k8s/ -n motd-api

# Check status
kubectl get pods -n motd-api
kubectl logs -f deployment/motd-embed-api -n motd-api
```

## Monitoring

### Health Checks

The `/health` endpoint returns:
```json
{"status": "ok"}
```

Configure your monitoring system to poll this endpoint:
- **Interval**: 30 seconds
- **Timeout**: 5 seconds
- **Retries**: 3

### Logging

Logs are written to stdout in structured format:
```
2024-01-20 10:30:45 - motd_embed_api.main - INFO - Starting server on 0.0.0.0:8000 (reload=False)
```

**Log aggregation options:**
- Docker logs driver (json-file, syslog, etc.)
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Loki + Grafana
- CloudWatch Logs (AWS)
- Cloud Logging (GCP)

### Metrics (Optional)

Consider adding Prometheus metrics:

```python
# Example: Add to main.py
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

Then scrape `/metrics` endpoint with Prometheus.

## Scaling

### Horizontal Scaling

The application is stateless (cache is in-memory per instance). For load balancing:

1. **Docker Compose scale:**
   ```bash
   docker-compose up -d --scale api=3
   ```

2. **Kubernetes replicas:**
   ```yaml
   spec:
     replicas: 3
   ```

3. **Add load balancer** in front of instances

**Note:** Each instance has its own cache. Consider Redis for shared caching if needed.

### Vertical Scaling

Adjust resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 256M
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs api

# Common issues:
# - Port 8000 already in use
# - Missing static files directory
# - Invalid environment variables
```

### High memory usage

- Check cache size (no max limit currently)
- Monitor number of unique servers queried
- Consider implementing LRU cache eviction

### Slow response times

- Check Minecraft server response times
- Verify cache is working (should see hits in logs)
- Check network connectivity to Minecraft servers

### CORS errors

- Verify `ALLOWED_ORIGINS` matches your domain exactly
- Check protocol (http vs https)
- Ensure no trailing slashes in origins

## Backup and Recovery

### Data

The application is stateless. No data backup needed.

### Configuration

Backup your `.env` file and any custom configurations:

```bash
# Backup
cp .env .env.backup

# Restore
cp .env.backup .env
docker-compose restart
```

## Rollback

```bash
# Docker Compose
docker-compose down
git checkout <previous-version>
docker-compose up -d

# Docker manual
docker stop motd-embed-api
docker rm motd-embed-api
docker run -d ... motd-embed-api:<previous-tag>

# Kubernetes
kubectl rollout undo deployment/motd-embed-api -n motd-api
```

## Security Updates

### Regular updates

```bash
# Rebuild with latest base image
docker-compose build --no-cache
docker-compose up -d
```

### Automated security scanning

```bash
# Scan image for vulnerabilities
docker scan motd-embed-api:latest

# Or use Trivy
trivy image motd-embed-api:latest
```

## Support

For issues or questions:
- Check logs first: `docker-compose logs -f`
- Review health endpoint: `curl http://localhost:8000/health`
- Check GitHub issues (if public repo)
