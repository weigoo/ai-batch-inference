from .config import config
from .redis_client import redis_client


STATUS_PREFIX = "status:"


def set_status(job_id: str, status: str, ttl: int = None):
    """
    Set job status with TTL
    
    Args:
        job_id: Job identifier
        status: Job status (QUEUED, RUNNING, COMPLETED, FAILED)
        ttl: Time to live in seconds (defaults to config.STATUS_TTL)
    """
    if ttl is None:
        ttl = config.STATUS_TTL
    
    key = STATUS_PREFIX + job_id
    redis_client.setex(key, ttl, status)


def get_status(job_id: str):
    """Get job status"""
    key = STATUS_PREFIX + job_id
    return redis_client.get(key)