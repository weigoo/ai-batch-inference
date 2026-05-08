# shared/queue.py

import json
import time
import uuid

from .redis_client import redis_client
from .status import set_status


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


def dequeue_job(timeout=5):
    """"Block until a job is available or timeout occurs"""
    result = redis_client.blpop(QUEUE_NAME, timeout=timeout)

    if result:
        return json.loads(result[1])

    return None


def get_queue_length():
    return redis_client.llen(QUEUE_NAME)


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