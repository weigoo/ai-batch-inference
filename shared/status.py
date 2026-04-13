import redis

redis_client = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True
)

STATUS_PREFIX = "status:"


def set_status(job_id, status):

    key = STATUS_PREFIX + job_id

    redis_client.set(key, status)


def get_status(job_id):

    key = STATUS_PREFIX + job_id

    return redis_client.get(key)