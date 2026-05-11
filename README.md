
# AI Batch Inference System

A distributed batch inference service for running AI models at scale using FastAPI, Redis, and scalable worker pools.

## Overview

This project implements a job-queue based architecture for processing batch inference requests. It decouples API requests from model execution, allowing horizontal scaling of worker processes to handle high throughput.

**Features:**
- REST API for submitting batch inference jobs
- Distributed worker processing with Redis job queue
- Job status tracking and result retrieval
- Prometheus metrics support
- Docker and Kubernetes deployment ready
- Sentiment analysis on input texts using DistilBERT

## Architecture

```
Client → API (FastAPI) → Redis Queue ↔ Workers (autoscaled by KEDA)
                         ↓
                    Job Storage & Status
                         ↓
                    Prometheus Metrics
```

**Components:**
- **API Service**: FastAPI server that accepts batch jobs and serves results
- **Worker Service**: Polling workers that fetch jobs from Redis queue, run inference, and store results
- **Redis**: Job queue, status tracking, and result storage
- **KEDA**: Event-driven autoscaling based on Redis queue depth
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards for metrics
- **Model**: Hugging Face `distilbert-base-uncased-finetuned-sst-2-english` for sentiment analysis

## API Endpoints

### Submit Job
```
POST /submit-job
Body: { "texts": ["text1", "text2", ...] }
Response (200): { "job_id": "<uuid>", "status": "queued" }
Response (413): { "detail": "Total text size exceeds 100KB limit" }
Response (422): { "detail": "Validation error" }
```

**Constraints:**
- Batch size: 1-1000 texts (configurable via `MAX_BATCH_SIZE`)
- Text length: 1-5000 characters each (configurable via `MAX_TEXT_LENGTH`)
- Total payload: Max 100KB
- Returns 413 if total size exceeds 100KB
- Returns 422 if validation fails (empty list, empty texts, etc.)

### Get Job Status
```
GET /status/{job_id}
Response (200): { "job_id": "<uuid>", "status": "QUEUED|RUNNING|COMPLETED|FAILED" }
Response (404): { "detail": "Status not found for job_id: <id>" }
Response (500): { "detail": "Internal server error" }
```

**Status values:**
- `QUEUED`: Waiting in queue for processing
- `RUNNING`: Currently being processed by a worker
- `COMPLETED`: Successfully completed
- `FAILED`: Failed after max retries (check logs for details)

### Fetch Results
```
GET /result/{job_id}
Response (200): { "job_id": "<uuid>", "result": [{"label": "POSITIVE/NEGATIVE", "score": 0.9}, ...] }
Response (404): { "detail": "Result not found for job_id: <id>" }
Response (500): { "detail": "Internal server error" }
```

**Result format:**
- Each item: `{"label": "POSITIVE" | "NEGATIVE", "score": 0.0-1.0}`
- Results expire after `RESULT_TTL` (default 30 days)
- 404 returned if job not found or results expired

### View Metrics
```
GET /metrics
Response (200): Prometheus format text output
Response (403): { "detail": "Forbidden" }
```

Returns Prometheus metrics including:
- `job_queue_length`: Current number of jobs in queue
- `api_requests_total`: Total requests by method/endpoint/status
- `api_processing_seconds`: Request processing time histogram by endpoint
- `job_processing_seconds`: Worker job processing time
- `jobs_completed_total`: Total completed jobs
- `jobs_failed_total`: Total failed jobs

**Security**: Restricted to private IPs and hosts in `METRICS_ALLOWED_HOSTS` (default: 127.0.0.1)

### Health Check
```
GET /
Response (200): { "status": "running" }
```
Basic health check that's always available.

```
GET /health
Response (200): { "status": "healthy" }
Response (503): { "detail": "Service unavailable: <error>" }
```
Detailed health check that verifies Redis connectivity. Returns 503 if Redis is down.

## Quick Start

### Docker Compose
```bash
docker-compose up
```
This starts:
- Redis on port 6379
- API on port 8000
- 3 Worker replicas

### Manual Setup
```bash
# Install API dependencies
pip install -r api/requirements.txt

# Install Worker dependencies
pip install -r worker/requirements.txt

# Start Redis
redis-server

# Start API
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Start workers (in another terminal)
python worker/worker.py
```

## Project Structure

```
.
├── api/                    # FastAPI application
│   ├── main.py            # REST API endpoints with Prometheus metrics
│   ├── Dockerfile
│   └── requirements.txt
├── worker/                # Worker process
│   ├── worker.py         # Job processing loop with retry logic
│   ├── Dockerfile
│   └── requirements.txt
├── shared/               # Shared utilities
│   ├── config.py        # Centralized environment-based configuration
│   ├── logging.py       # Structured JSON logging setup
│   ├── model.py         # Model loading & inference with caching
│   ├── queue.py         # Redis job queue and DLQ operations
│   ├── redis_client.py  # Redis connection management
│   ├── status.py        # Job status tracking with TTL
│   └── storage.py       # Result storage with auto-expiration
├── tests/                # Test suite
│   ├── conftest.py      # Pytest configuration and mocks
│   ├── test_api.py      # API endpoint tests
│   └── requirements.txt
├── k8s/                 # Kubernetes manifests
│   ├── api.yaml
│   ├── grafana.yaml
│   ├── prometheus.yaml
│   ├── prometheus-rules.yaml
│   ├── redis.yaml
│   ├── worker.yaml
│   ├── worker-keda.yaml
│   └── worker-pdb.yaml
├── docker-compose.yml
├── CONFIG.md            # Environment variable configuration reference
├── IMPLEMENTATION_SUMMARY.md  # Code review fixes and improvements
└── CODE_REVIEW.md       # Comprehensive code review findings
```

## Dependencies

### API Service (`api/requirements.txt`)
- **fastapi**: Web framework with async support
- **uvicorn**: ASGI server for running FastAPI
- **redis**: Redis client for queue and state operations
- **pydantic**: Data validation and serialization
- **prometheus-client**: Prometheus metrics collection and export
- **python-json-logger**: Structured JSON logging
- **slowapi**: Rate limiting for API endpoints

### Worker Service (`worker/requirements.txt`)
- **torch**: PyTorch neural network framework
- **transformers**: Hugging Face model library for inference
- **redis**: Redis client for queue operations
- **prometheus-client**: Prometheus metrics collection
- **python-json-logger**: Structured JSON logging

### Test Dependencies (`tests/requirements.txt`)
- **pytest**: Testing framework
- **pytest-cov**: Code coverage plugin
- **pytest-asyncio**: Async test support
- **httpx**: HTTP client for testing API endpoints
- **fastapi**: For TestClient in integration tests
- **redis**: For mocking Redis operations

## Configuration

All configuration is managed through **environment variables** for flexibility across dev/staging/prod environments. See [CONFIG.md](CONFIG.md) for a complete reference of all available configuration options.

Key configuration categories:
- **Redis**: Connection settings (host, port, password, SSL)
- **Model**: Model selection and device (CPU/CUDA)
- **Inference**: Batch size limits, text length constraints, timeouts
- **Worker**: Polling interval, retry logic, exponential backoff
- **Storage**: TTL for results and status (default 30 days)
- **Security**: Metrics endpoint access control, rate limiting
- **Logging**: Structured JSON logging with configurable levels

Example:
```bash
export REDIS_HOST=redis.default.svc.cluster.local
export LOG_LEVEL=INFO
export MAX_BATCH_SIZE=1000
export WORKER_MAX_RETRIES=3
export METRICS_ALLOWED_HOSTS=127.0.0.1,prometheus
```

## Testing

The project includes a comprehensive test suite using pytest with Redis mocking.

### Run All Tests
```bash
pip install -r tests/requirements.txt
pytest
```

### Run Tests with Coverage
```bash
pytest --cov=api --cov=worker --cov=shared --cov-report=html
```

### Run Specific Test Classes
```bash
pytest tests/test_api.py::TestSubmitJob  # Job submission tests
pytest tests/test_api.py::TestMetricsEndpoint  # Metrics endpoint tests
```

### Test Features
- **Unit tests**: API endpoint validation, error handling, response formats
- **Mock Redis**: Redis operations mocked to avoid external dependencies
- **Pydantic validation**: Input validation and constraint enforcement
- **Error scenarios**: Tests for edge cases (empty lists, oversized text, invalid job IDs)
- **Metrics**: Prometheus metric recording and collection verification

## Kubernetes Deployment

### Prerequisites
- KEDA must be installed in your cluster:
```bash
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda --namespace keda --create-namespace
```

### Deploy
```bash
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/worker.yaml
kubectl apply -f k8s/worker-keda.yaml
kubectl apply -f k8s/prometheus.yaml
kubectl apply -f k8s/grafana.yaml
```

KEDA automatically scales workers based on Redis queue depth. Grafana provides real-time monitoring dashboards.

## Security Considerations

### Metrics Endpoint Protection
The `/metrics` endpoint is restricted to private IP addresses and explicitly allowed hosts:
- Configured via `METRICS_ALLOWED_HOSTS` environment variable
- Default: `127.0.0.1` (localhost only)
- Production: Add internal monitoring service IPs

### Redis Security
- Use `REDIS_PASSWORD` for authentication in production
- Enable `REDIS_SSL` for encrypted connections
- Restrict Redis to private network namespaces in Kubernetes
- Never expose Redis ports externally

### API Rate Limiting
- Rate limiting enabled by default (100 requests/minute)
- Configure via `RATE_LIMIT` environment variable
- Prevents DOS attacks and resource exhaustion

### Input Validation
- All text inputs validated for length (`MAX_TEXT_LENGTH`: 5000 chars)
- Batch size limited (`MAX_BATCH_SIZE`: 1000 texts)
- Total payload size capped at 100KB
- Invalid requests return 422 or 413 HTTP errors

## Troubleshooting

### KEDA Scaling Issues

**Issue: Workers don't scale up when jobs are queued**

Common causes and solutions:
1. **Static replicas** in worker.yaml override KEDA - remove the `replicas:` field
2. **Redis connectivity** - verify Redis is in the correct namespace:
   ```bash
   kubectl get svc --all-namespaces | grep redis
   kubectl logs -n keda deployment/keda-operator | grep -i redis
   ```
3. **ScaledObject not active** - check KEDA operator and ScaledObject status:
   ```bash
   kubectl describe scaledobject worker-queue-scaler -n default
   kubectl logs -n keda deployment/keda-operator
   ```
4. **Queue threshold too high** - adjust `activationThreshold` in worker-keda.yaml if queue frequently exceeds threshold

### Health Check Issues

**Issue: `/health` endpoint returns 503 "Service unavailable"**

Common causes:
1. Redis connection failed - check `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
2. Network connectivity - verify Redis service is accessible from API pod
   ```bash
   kubectl exec -it <api-pod> -- redis-cli -h redis ping
   ```

### Job Processing Issues

**Issue: Jobs stuck in RUNNING state**

Causes:
1. Worker crashed during processing - check worker logs: `kubectl logs <worker-pod>`
2. Inference timeout exceeded - increase `INFERENCE_TIMEOUT` or check model/hardware
3. Dead letter queue - failed jobs moved to DLQ after max retries

**Issue: High memory usage**

Solutions:
1. Results/status auto-expire after `RESULT_TTL` (default 30 days) - verify TTL is set
2. Reduce `INFERENCE_TIMEOUT` to release resources faster
3. Scale workers if single worker is overloaded: `kubectl scale deployment worker --replicas=5`

### Metrics Issues

**Issue: Metrics endpoint returns 403 Forbidden**

Causes:
1. Client IP not in `METRICS_ALLOWED_HOSTS` - add client IP to configuration
2. Prometheus service account needs network policy exception
3. Check current allowed hosts: `kubectl get deployment api -o yaml | grep METRICS_ALLOWED_HOSTS`

### Testing Issues

**Issue: Tests fail with Redis connection errors**

Solutions:
1. Ensure Redis is properly mocked in conftest.py
2. Run tests with verbose output: `pytest -v tests/test_api.py`
3. Check Python version compatibility: Python 3.9+
4. Verify all test dependencies installed: `pip install -r tests/requirements.txt`

## Job Lifecycle

1. **Submit**: Client posts texts to `/submit-job` with validation
2. **Queue**: Job is added to Redis queue with status `QUEUED`
3. **Process**: Worker dequeues job, sets status to `RUNNING`, runs inference with retries
4. **Store**: Results saved to Redis with 30-day TTL, status set to `COMPLETED`
5. **Retrieve**: Client fetches results via `/result/{job_id}`
6. **Expire**: Job status and results auto-expire after TTL period

## Error Handling & Resilience

### Retry Logic
Workers automatically retry failed jobs with exponential backoff:
- **Max retries**: 3 attempts (configurable via `WORKER_MAX_RETRIES`)
- **Backoff multiplier**: 2.0x exponential backoff (configurable via `WORKER_RETRY_BACKOFF`)
- **Model errors**: Trigger immediate DLQ for manual review
- **Transient errors**: Retried with backoff before DLQ placement

### Dead Letter Queue (DLQ)
- Failed jobs after max retries are moved to DLQ for analysis
- Prevents infinite retry loops and job loss
- Monitor DLQ for operational insights

### Graceful Shutdown
- Workers handle SIGTERM and SIGINT signals
- Complete in-flight jobs before terminating
- Prevent data loss during deployments

## Monitoring & Observability

### Structured Logging
All services use structured JSON logging for machine-parseable logs:
```json
{"timestamp": "2026-05-10T12:00:00.000Z", "level": "INFO", "logger": "api.main", "job_id": "uuid-123", "text_count": 5, "message": "Job submitted"}
```

### Prometheus Metrics
**Queue Metrics:**
- `job_queue_length`: Current number of jobs in queue

**API Metrics:**
- `api_requests_total`: Total requests by method/endpoint/status
- `api_processing_seconds`: Request processing time histogram by endpoint

**Worker Metrics:**
- `job_processing_seconds`: Job inference processing time
- `jobs_completed_total`: Total completed jobs
- `jobs_failed_total`: Total failed jobs

**Metrics endpoint**: `GET /metrics` (restricted to private IPs and configured hosts)

### Grafana Dashboards
Pre-configured dashboards available in Kubernetes deployment for:
- Queue depth over time
- API response times
- Worker throughput
- Job success/failure rates

## Scaling

### Automatic Scaling with KEDA
Workers are automatically scaled based on Redis queue depth using KEDA ScaledObject:
- **Min replicas**: 1 (minimum worker to handle jobs)
- **Max replicas**: 5 (prevents runaway scaling)
- **Target**: Scales based on Redis queue length
- **Polling interval**: 5 seconds (checks queue depth every 5 seconds)
- **Cooldown period**: 60 seconds (waits before scaling down)
- **Activation threshold**: 5 jobs (minimum queue depth to trigger scaling)

The ScaledObject monitors Redis list length and adjusts replicas to maintain queue processing:
```yaml
scaler:
  - type: redis
    metadata:
      address: redis.default.svc.cluster.local:6379
      listName: job_queue
      databaseIndex: "0"
      activationThreshold: "5"
      listLength: "10"
```

When queue depth exceeds the activation threshold, workers scale up. When queue empties, they scale down to the minimum.

### Manual Scaling (Docker Compose)
In `docker-compose.yml`, adjust worker replicas:
```yaml
services:
  worker:
    deploy:
      replicas: 3  # Change to desired number
```

### Performance Tuning
- **Model caching**: Model is loaded once per worker process and cached in memory
- **Worker polling**: Configurable polling interval (default 2 seconds) - balance latency vs CPU
- **Batch optimization**: Queue supports batch dequeue for future throughput optimization
- **Inference timeout**: Configure `INFERENCE_TIMEOUT` based on model complexity and hardware
- **KEDA thresholds**: Adjust `activationThreshold` and `listLength` based on your SLA requirements

## Troubleshooting

### KEDA Scaling Issues

**Issue: Workers don't scale up when jobs are queued**

Common causes and solutions:
1. **Static replicas** in worker.yaml override KEDA - remove the `replicas:` field
2. **Redis connectivity** - verify Redis is in the correct namespace:
   ```bash
   kubectl get svc --all-namespaces | grep redis
   kubectl logs -n keda deployment/keda-operator | grep -i redis
   ```
3. **ScaledObject not active** - check KEDA operator and ScaledObject status:
   ```bash
   kubectl describe scaledobject worker-queue-scaler -n default
   kubectl logs -n keda deployment/keda-operator
   ```
4. **Queue threshold too high** - adjust `activationThreshold` in worker-keda.yaml if queue frequently exceeds threshold

### Health Check Issues

**Issue: `/health` endpoint returns 503 "Service unavailable"**

Common causes:
1. Redis connection failed - check `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
2. Network connectivity - verify Redis service is accessible from API pod
   ```bash
   kubectl exec -it <api-pod> -- redis-cli -h redis ping
   ```

### Job Processing Issues

**Issue: Jobs stuck in RUNNING state**

Causes:
1. Worker crashed during processing - check worker logs: `kubectl logs <worker-pod>`
2. Inference timeout exceeded - increase `INFERENCE_TIMEOUT` or check model/hardware
3. Dead letter queue - failed jobs moved to DLQ after max retries

**Issue: High memory usage**

Solutions:
1. Results/status auto-expire after `RESULT_TTL` (default 30 days) - verify TTL is set
2. Reduce `INFERENCE_TIMEOUT` to release resources faster
3. Scale workers if single worker is overloaded: `kubectl scale deployment worker --replicas=5`

### Metrics Issues

**Issue: Metrics endpoint returns 403 Forbidden**

Causes:
1. Client IP not in `METRICS_ALLOWED_HOSTS` - add client IP to configuration
2. Prometheus service account needs network policy exception
3. Check current allowed hosts: `kubectl get deployment api -o yaml | grep METRICS_ALLOWED_HOSTS`

### Testing Issues

**Issue: Tests fail with Redis connection errors**

Solutions:
1. Ensure Redis is properly mocked in conftest.py
2. Run tests with verbose output: `pytest -v tests/test_api.py`
3. Check Python version compatibility: Python 3.9+
4. Verify all test dependencies installed: `pip install -r tests/requirements.txt`

## Documentation & References

- **[CONFIG.md](CONFIG.md)**: Complete environment variable configuration reference

## Contributing

When making changes:
1. Ensure all tests pass: `pytest`
2. Check code coverage: `pytest --cov`
3. Update documentation in README.md and CONFIG.md
4. Use structured logging: `logger.info("message", extra={"key": "value"})`
5. Follow environment variable conventions for configuration

## License & Support

For issues, questions, or contributions, refer to the project documentation files above.

