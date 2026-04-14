
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
Response: { "job_id": "<uuid>", "status": "queued" }
```

### Get Job Status
```
GET /status/{job_id}
Response: { "job_id": "<uuid>", "status": "QUEUED|RUNNING|COMPLETED|FAILED" }
```

### Fetch Results
```
GET /result/{job_id}
Response: { "job_id": "<uuid>", "result": [{"label": "POSITIVE/NEGATIVE", "score": 0.9}, ...] }
```

### View Metrics
```
GET /metrics
Response: { "queue_length": 5, "jobs_completed": 42 }
```

### Health Check
```
GET /
Response: { "status": "running" }
```

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
│   ├── main.py            # REST API endpoints
│   └── Dockerfile
├── worker/                # Worker process
│   ├── worker.py         # Job processing loop
│   └── Dockerfile
├── shared/               # Shared utilities
│   ├── model.py         # Model loading & inference
│   ├── queue.py         # Redis job queue operations
│   ├── status.py        # Status tracking
│   └── storage.py       # Result storage
├── k8s/                 # Kubernetes manifests
│   ├── api.yaml
│   ├── grafana.yaml
│   ├── prometheus.yaml
│   ├── redis.yaml
│   ├── worker.yaml
│   └── worker-keda.yaml
├── docker-compose.yml
├── api/requirements.txt
└── worker/requirements.txt
```

## Dependencies

### API Service (`api/requirements.txt`)
- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **redis**: In-memory data store
- **pydantic**: Data validation
- **prometheus-client**: Metrics collection

### Worker Service (`worker/requirements.txt`)
- **torch**: PyTorch neural network framework
- **transformers**: Hugging Face model library
- **redis**: In-memory data store
- **prometheus-client**: Metrics collection

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

KEDA will automatically scale workers based on Redis queue depth. Grafana provides real-time monitoring dashboards.

## Troubleshooting KEDA Scaling

**Issue: Workers don't scale up when jobs are queued**

Common causes:
1. **Static replicas** in worker.yaml override KEDA - remove the `replicas:` field
2. **Redis connectivity** - verify Redis is in the correct namespace:
   ```bash
   kubectl get svc --all-namespaces | grep redis
   ```
3. **ScaledObject not active** - check KEDA logs:
   ```bash
   kubectl logs -n keda deployment/keda-operator
   kubectl describe scaledobject worker-queue-scaler
   ```
4. **Queue threshold too high** - adjust `activationThreshold` and `listLength` in worker-keda.yaml

## Job Lifecycle

1. **Submit**: Client posts texts to `/submit-job`
2. **Queue**: Job is added to Redis queue with status `QUEUED`
3. **Process**: Worker dequeues job, sets status to `RUNNING`, runs inference
4. **Store**: Results saved to Redis, status set to `COMPLETED`
5. **Retrieve**: Client fetches results via `/result/{job_id}`

## Scaling

### Automatic Scaling with KEDA
Workers are automatically scaled based on Redis queue depth:
- **Min replicas**: 1 (minimum worker to handle jobs)
- **Max replicas**: 5 (prevents runaway scaling)
- **Polling interval**: 5 seconds (checks queue depth every 5 seconds)
- **Cooldown period**: 60 seconds (waits before scaling down)
- **Trigger**: Scales when queue has jobs, scales down when empty

Configuration in `k8s/worker-keda.yaml`:
```yaml
metadata:
  address: redis.default.svc.cluster.local:6379
  listName: job_queue
  databaseIndex: "0"
  activationThreshold: "5"
  listLength: "10"
```

### Manual Scaling (Docker Compose)
In `docker-compose.yml`, adjust worker replicas:
```yaml
deploy:
  replicas: 3  # Change to desired number
```

### Performance Tuning
- Model is cached in-process to avoid reloading per job
- Workers poll every 2 seconds for new jobs
- Adjust thresholds in worker-keda.yaml to match your inference latency and throughput needs

---
