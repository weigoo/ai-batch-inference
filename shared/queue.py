# shared/queue.py

import json
import time
import uuid

import redis

from .config import config
from .status import set_status

# Initialize Redis client with config
redis_client = redis.Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    password=config.REDIS_PASSWORD if config.REDIS_PASSWORD else None,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_keepalive=True,
    ssl=config.REDIS_SSL,
)

QUEUE_NAME = "job_queue"
DLQ_NAME = "job_dlq"

def enqueue_job(texts):
    job_id = str(uuid.uuid4())

    set_status(job_id, "QUEUED")

    job_data = {
        "job_id": job_id,
        "texts": texts
    }

    redis_client.rpush(
        QUEUE_NAME,
        json.dumps(job_data)
    )

    return job_id


def dequeue_job():
    job = redis_client.lpop(QUEUE_NAME)

    if job:
        return json.loads(job)

    return None


def get_queue_length():
    return redis_client.llen(QUEUE_NAME)


def dequeue_batch(batch_size: int = 1):
    """
    Dequeue multiple jobs at once for batch inference optimization
    
    Args:
        batch_size: Number of jobs to dequeue
        
    Returns:
        List of job dicts
    """
    jobs = []
    
    for _ in range(batch_size):
        data = redis_client.lpop(QUEUE_NAME)
        
        if data is None:
            break
        
        job = json.loads(data)
        jobs.append(job)
    
    return jobs


def send_to_dlq(job: dict, reason: str):
    """
    Send failed job to Dead Letter Queue for manual review
    
    Args:
        job: The job dict that failed
        reason: Reason for failure
    """
    dlq_entry = {
        "job": job,
        "failed_reason": reason,
        "timestamp": time.time()
    }
    redis_client.rpush(DLQ_NAME, json.dumps(dlq_entry))


def get_dlq_length():
    """Get number of jobs in dead letter queue"""
    return redis_client.llen(DLQ_NAME)