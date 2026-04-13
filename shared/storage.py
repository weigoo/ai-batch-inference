import json

import redis

redis_client = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True
)

RESULT_PREFIX = "result:"


def store_result(job_id, result):

    key = RESULT_PREFIX + job_id

    redis_client.set(
        key,
        json.dumps(result)
    )


def get_result(job_id):

    key = RESULT_PREFIX + job_id

    result = redis_client.get(key)

    if result:
        return json.loads(result)

    return None


COUNTER_KEY = "jobs_completed"


def increment_completed():

    redis_client.incr(COUNTER_KEY)


def get_completed():

    value = redis_client.get(COUNTER_KEY)

    return int(value) if value else 0    