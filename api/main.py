# api/main.py

import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field, validator

from shared.config import config
from shared.logging import setup_logging
from shared.queue import enqueue_job, get_queue_length
from shared.status import get_status
from shared.storage import get_completed, get_result

logger = setup_logging(__name__, config.LOG_LEVEL)

# Prometheus metrics
queue_gauge = Gauge(
    "job_queue_length",
    "Number of jobs in queue"
)

api_requests = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"]
)

processing_latency = Histogram(
    "api_processing_seconds",
    "API request processing time",
    ["endpoint"]
)

# Request/Response Models
class JobRequest(BaseModel):
    """Batch job submission request"""
    texts: list[str] = Field(
        ...,
        min_items=1,
        max_items=config.MAX_BATCH_SIZE,
        description="Texts to analyze"
    )
    
    @validator('texts')
    def validate_text_content(cls, v):
        """Validate individual text items"""
        for i, text in enumerate(v):
            if not isinstance(text, str):
                raise ValueError(f'texts[{i}] must be string')
            if not text or not text.strip():
                raise ValueError(f'texts[{i}] cannot be empty')
            if len(text) > config.MAX_TEXT_LENGTH:
                raise ValueError(
                    f'texts[{i}] exceeds max length {config.MAX_TEXT_LENGTH}'
                )
        return v


class JobResponse(BaseModel):
    """Job submission response"""
    job_id: str
    status: str


class ResultResponse(BaseModel):
    """Result retrieval response"""
    job_id: str
    result: list


class StatusResponse(BaseModel):
    """Job status response"""
    job_id: str
    status: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    reason: str = None


app = FastAPI(
    title="AI Batch Inference API",
    description="Distributed batch inference service",
    version="1.0.0"
)


@app.post("/submit-job", response_model=JobResponse, status_code=200)
async def submit_job(request: JobRequest):
    """
    Submit a batch job for inference
    
    Args:
        request: JobRequest with list of texts
        
    Returns:
        JobResponse with job_id and status
    """
    try:
        # Calculate total size
        total_chars = sum(len(t) for t in request.texts)
        if total_chars > 100_000:  # 100KB limit
            api_requests.labels(
                method="POST",
                endpoint="/submit-job",
                status=413
            ).inc()
            raise HTTPException(
                status_code=413,
                detail="Total text size exceeds 100KB limit"
            )
        
        job_id = enqueue_job(request.texts)
        
        logger.info("Job submitted", extra={
            "job_id": job_id,
            "text_count": len(request.texts),
            "total_chars": total_chars
        })
        
        api_requests.labels(
            method="POST",
            endpoint="/submit-job",
            status=200
        ).inc()
        
        return JobResponse(job_id=job_id, status="queued")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error submitting job: %s", e)
        api_requests.labels(
            method="POST",
            endpoint="/submit-job",
            status=500
        ).inc()
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="running")


@app.get("/health", response_model=HealthResponse)
async def detailed_health_check():
    """Detailed health check with Redis connectivity test"""
    try:
        from shared.queue import redis_client
        redis_client.ping()
        
        api_requests.labels(
            method="GET",
            endpoint="/health",
            status=200
        ).inc()
        
        return HealthResponse(status="healthy")
        
    except Exception as e:
        logger.error("Health check failed: %s", e)
        api_requests.labels(
            method="GET",
            endpoint="/health",
            status=503
        ).inc()
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )


@app.get("/result/{job_id}", response_model=ResultResponse, status_code=200)
async def fetch_result(job_id: str):
    """
    Fetch job results
    
    Args:
        job_id: Job identifier
        
    Returns:
        ResultResponse with results
    """
    try:
        result = get_result(job_id)
        
        if result is None:
            api_requests.labels(
                method="GET",
                endpoint="/result/{job_id}",
                status=404
            ).inc()
            raise HTTPException(
                status_code=404,
                detail=f"Result not found for job_id: {job_id}"
            )
        
        api_requests.labels(
            method="GET",
            endpoint="/result/{job_id}",
            status=200
        ).inc()
        
        return ResultResponse(job_id=job_id, result=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching result: %s", e)
        api_requests.labels(
            method="GET",
            endpoint="/result/{job_id}",
            status=500
        ).inc()
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.get("/status/{job_id}", response_model=StatusResponse, status_code=200)
async def job_status(job_id: str):
    """
    Get job processing status
    
    Args:
        job_id: Job identifier
        
    Returns:
        StatusResponse with current status
    """
    try:
        status = get_status(job_id)
        
        if status is None:
            api_requests.labels(
                method="GET",
                endpoint="/status/{job_id}",
                status=404
            ).inc()
            raise HTTPException(
                status_code=404,
                detail=f"Status not found for job_id: {job_id}"
            )
        
        api_requests.labels(
            method="GET",
            endpoint="/status/{job_id}",
            status=200
        ).inc()
        
        return StatusResponse(job_id=job_id, status=status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching status: %s", e)
        api_requests.labels(
            method="GET",
            endpoint="/status/{job_id}",
            status=500
        ).inc()
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.get("/metrics")
async def prometheus_metrics(request: Request):
    """
    Prometheus metrics endpoint (internal only)
    
    Restricts access to internal clients to prevent exposure of sensitive metrics
    """
    # Restrict metrics endpoint to internal IPs
    client_host = request.client.host if request.client else "unknown"    
    
    import ipaddress
    is_private = False
    try:
        is_private = ipaddress.ip_address(client_host).is_private
    except ValueError:
        pass

    if not is_private and client_host not in config.METRICS_ALLOWED_HOSTS:
        logger.warning("Unauthorized metrics access from %s", client_host)
        api_requests.labels(
            method="GET",
            endpoint="/metrics",
            status=403
        ).inc()
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
    
    try:
        queue_length = get_queue_length()
        queue_gauge.set(queue_length)
        
        api_requests.labels(
            method="GET",
            endpoint="/metrics",
            status=200
        ).inc()
        
        return Response(
            generate_latest(),
            media_type="text/plain"
        )
    except Exception as e:
        logger.exception("Error generating metrics: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate metrics"
        )
