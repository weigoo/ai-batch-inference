
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
Client → API (FastAPI) → Redis Queue ↔ Workers (x3)
                         ↓
                    Job Storage & Status
```

**Components:**
- **API Service**: FastAPI server that accepts batch jobs and serves results
- **Worker Service**: Polling workers that fetch jobs from Redis queue, run inference, and store results
- **Redis**: Job queue, status tracking, and result storage
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
# Install dependencies
pip install -r requirements.txt

# Start Redis
redis-server

# Start API
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Start workers
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
│   ├── redis.yaml
│   └── worker.yaml
├── docker-compose.yml
└── requirements.txt
```

## Dependencies

- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **redis**: In-memory data store
- **transformers**: Hugging Face model library
- **torch**: PyTorch (for transformers)
- **pydantic**: Data validation
- **prometheus-client**: Metrics collection

## Kubernetes Deployment

```bash
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/worker.yaml
```

## Job Lifecycle

1. **Submit**: Client posts texts to `/submit-job`
2. **Queue**: Job is added to Redis queue with status `QUEUED`
3. **Process**: Worker dequeues job, sets status to `RUNNING`, runs inference
4. **Store**: Results saved to Redis, status set to `COMPLETED`
5. **Retrieve**: Client fetches results via `/result/{job_id}`

## Scaling

- Increase worker replicas in docker-compose.yml or worker.yaml
- Workers automatically fetch from the shared Redis queue
- Model is cached in-process to avoid reloading per job

---
