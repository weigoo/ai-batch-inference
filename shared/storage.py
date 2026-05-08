import json
import redis

from .config import config

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

RESULT_PREFIX = "result:"
COUNTER_KEY = "jobs_completed"


def store_result(job_id: str, result, ttl: int = None):
    """
    Store job result with TTL
    
    Args:
        job_id: Job identifier
        result: Result data to store
        ttl: Time to live in seconds (defaults to config.RESULT_TTL)
    """
    if ttl is None:
        ttl = config.RESULT_TTL
    
    key = RESULT_PREFIX + job_id
    redis_client.setex(
        key,
        ttl,
        json.dumps(result)
    )


def get_result(job_id: str):
    """Get stored result"""
    key = RESULT_PREFIX + job_id
    result = redis_client.get(key)
    
    if result:
        return json.loads(result)
    
    return None


def increment_completed():
    """Increment job completion counter"""
    redis_client.incr(COUNTER_KEY)


def get_completed():
    """Get total completed jobs count"""
    value = redis_client.get(COUNTER_KEY)
    return int(value) if value else 0    