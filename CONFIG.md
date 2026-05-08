# Configuration Guide

## Environment Variables

All configuration is managed through environment variables. This allows for easy customization across different environments (dev, staging, prod).

### Redis Configuration
- `REDIS_HOST`: Redis hostname (default: `localhost`)
- `REDIS_PORT`: Redis port (default: `6379`)
- `REDIS_DB`: Redis database number (default: `0`)
- `REDIS_PASSWORD`: Redis password for authentication (default: empty)
- `REDIS_SSL`: Enable SSL for Redis connection (default: `False`)

### Model Configuration
- `MODEL_NAME`: Hugging Face model identifier (default: `distilbert-base-uncased-finetuned-sst-2-english`)
- `MODEL_DEVICE`: PyTorch device (`cpu` or `cuda`) (default: `cpu`)

### Inference Configuration
- `INFERENCE_TIMEOUT`: Maximum inference time in seconds (default: `300`)
- `MAX_BATCH_SIZE`: Maximum number of texts per batch (default: `1000`)
- `MAX_TEXT_LENGTH`: Maximum length per text in characters (default: `5000`)

### Worker Configuration
- `WORKER_POLLING_INTERVAL`: Polling interval in seconds (default: `2`)
- `WORKER_MAX_RETRIES`: Maximum retry attempts per job (default: `3`)
- `WORKER_RETRY_BACKOFF`: Exponential backoff multiplier (default: `2.0`)

### API Configuration
- `API_HOST`: API listening host (default: `0.0.0.0`)
- `API_PORT`: API listening port (default: `8000`)

### Logging Configuration
- `LOG_LEVEL`: Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) (default: `INFO`)

### Storage Configuration
- `RESULT_TTL`: Result storage time-to-live in seconds (default: `2592000` = 30 days)
- `STATUS_TTL`: Job status TTL in seconds (default: `2592000` = 30 days)

### Security Configuration
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins (default: `localhost`)
- `ENABLE_RATE_LIMITING`: Enable rate limiting (default: `True`)
- `RATE_LIMIT`: Rate limit specification (default: `100/minute`)

## Example Configuration

### Docker Compose
```bash
# .env file
REDIS_HOST=redis
LOG_LEVEL=INFO
MAX_BATCH_SIZE=500
RESULT_TTL=604800  # 7 days
```

### Kubernetes
```yaml
env:
  - name: REDIS_HOST
    value: redis.default.svc.cluster.local
  - name: LOG_LEVEL
    value: "INFO"
  - name: INFERENCE_TIMEOUT
    value: "300"
  - name: MAX_BATCH_SIZE
    value: "1000"
```

## Production Settings

For production deployment, consider:

```bash
# Security
REDIS_PASSWORD=<strong-password>
REDIS_SSL=True
ALLOWED_ORIGINS=api.example.com,app.example.com
ENABLE_RATE_LIMITING=True

# Performance
INFERENCE_TIMEOUT=600
MAX_BATCH_SIZE=2000
WORKER_MAX_RETRIES=5

# Monitoring
LOG_LEVEL=INFO
RESULT_TTL=2592000  # 30 days for audit trail
```
