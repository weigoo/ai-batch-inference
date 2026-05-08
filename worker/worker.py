"""
Worker service for batch inference
Processes jobs from Redis queue with retry logic and graceful shutdown
"""

import os
import signal
import sys
import time

from prometheus_client import Counter, Histogram

from shared.config import config
from shared.logging import setup_logging
from shared.model import run_inference, ModelError, get_model
from shared.queue import dequeue_job, send_to_dlq
from shared.status import set_status
from shared.storage import increment_completed, store_result

logger = setup_logging(__name__, config.LOG_LEVEL)

# Prometheus metrics
job_latency = Histogram(
    "job_processing_seconds",
    "Time spent processing jobs"
)

jobs_completed = Counter(
    "jobs_completed_total",
    "Total jobs completed"
)

jobs_failed = Counter(
    "jobs_failed_total",
    "Total jobs failed"
)


class WorkerShutdownSignal(Exception):
    """Exception to signal graceful shutdown"""
    pass


def handle_shutdown(signum, frame):
    """Signal handler for graceful shutdown"""
    logger.info("Received signal %d, initiating graceful shutdown", signum)
    raise WorkerShutdownSignal()


def process_job(job: dict, max_retries: int = None):
    """
    Process a single job with retry logic
    
    Args:
        job: Job dict with job_id and texts
        max_retries: Max number of retry attempts
    """
    if max_retries is None:
        max_retries = config.WORKER_MAX_RETRIES
    
    job_id = job["job_id"]
    texts = job["texts"]
    
    for attempt in range(max_retries):
        try:
            logger.info("Processing job", extra={
                "job_id": job_id,
                "attempt": attempt + 1,
                "max_attempts": max_retries,
                "text_count": len(texts)
            })
            
            set_status(job_id, "RUNNING")
            
            with job_latency.time():
                results = run_inference(texts)
            
            store_result(job_id, results)
            increment_completed()
            set_status(job_id, "COMPLETED")
            
            jobs_completed.inc()
            
            logger.info("Job completed successfully", extra={
                "job_id": job_id,
                "result_count": len(results)
            })
            
            break  # Success, exit retry loop
            
        except ModelError as e:
            logger.error("Model error processing job", extra={
                "job_id": job_id,
                "error": str(e),
                "attempt": attempt + 1
            }, exc_info=True)
            
            # Model errors typically need human intervention
            if attempt == max_retries - 1:
                set_status(job_id, "FAILED")
                send_to_dlq(job, f"Model error: {str(e)}")
                jobs_failed.inc()
            else:
                backoff = config.WORKER_RETRY_BACKOFF ** attempt
                logger.info("Retrying after backoff", extra={
                    "job_id": job_id,
                    "backoff_seconds": backoff
                })
                time.sleep(backoff)
                
        except Exception as e:
            logger.error("Unexpected error processing job", extra={
                "job_id": job_id,
                "error": str(e),
                "attempt": attempt + 1
            }, exc_info=True)
            
            if attempt == max_retries - 1:
                set_status(job_id, "FAILED")
                send_to_dlq(job, f"Processing error: {str(e)}")
                jobs_failed.inc()
                logger.error("Job moved to DLQ after max retries", extra={
                    "job_id": job_id
                })
            else:
                # Exponential backoff with jitter
                backoff = config.WORKER_RETRY_BACKOFF ** attempt
                logger.info("Retrying after backoff", extra={
                    "job_id": job_id,
                    "backoff_seconds": backoff
                })
                time.sleep(backoff)


def worker_loop():
    """Main worker loop - continuously process jobs from queue"""
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    # Preload model on startup to ensure startup probe passes
    logger.info("Preloading model on startup")
    try:
        get_model()
        logger.info("Model preloaded successfully")
        # Create readiness file to signal startup probe
        with open("/tmp/worker_ready", "w") as f:
            f.write("ready")
        logger.info("Readiness file created")
    except ModelError as e:
        logger.error("Failed to preload model on startup: %s", e, exc_info=True)
        sys.exit(1)
    
    logger.info("Worker started", extra={
        "pid": os.getpid(),
        "polling_interval": config.WORKER_POLLING_INTERVAL,
        "max_retries": config.WORKER_MAX_RETRIES
    })
    
    try:
        while True:
            try:
                job = dequeue_job()
                
                if job:
                    process_job(job)
                else:
                    # No job available, sleep before next poll
                    time.sleep(config.WORKER_POLLING_INTERVAL)
                    
            except WorkerShutdownSignal:
                logger.info("Shutdown signal received, exiting gracefully")
                break
                
            except Exception as e:
                logger.exception("Unexpected error in worker loop: %s", e)
                # Backoff before retry to avoid tight failure loop
                time.sleep(5)
                
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        logger.info("Worker shutting down")


if __name__ == "__main__":
    try:
        worker_loop()
    except Exception as e:
        logger.exception("Fatal error in worker: %s", e)
        sys.exit(1)
