# shared/queue.py

import json
import uuid

import redis

from shared.status import set_status

redis_client = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True
)

QUEUE_NAME = "job_queue"

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


def dequeue_batch(batch_size=4):
    import redis
    import json

    jobs = []

    for _ in range(batch_size):

        data = redis_client.lpop(QUEUE_NAME)

        if data is None:
            break

        job = json.loads(data)

        jobs.append(job)

    return jobs