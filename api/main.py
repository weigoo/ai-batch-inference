# api/main.py

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import Gauge, generate_latest
from pydantic import BaseModel

from shared.queue import enqueue_job, get_queue_length
from shared.status import get_status
from shared.storage import get_completed, get_result

queue_gauge = Gauge(
    "job_queue_length",
    "Number of jobs in queue"
)

app = FastAPI()

class JobRequest(BaseModel):
    texts: list[str]


@app.post("/submit-job")
def submit_job(request: JobRequest):

    job_id = enqueue_job(
        request.texts
    )

    return {
        "job_id": job_id,
        "status": "queued"
    }


@app.get("/")
def health_check():
    return {
        "status": "running"
    }


@app.get("/result/{job_id}")
def fetch_result(job_id: str):

    result = get_result(job_id)

    if result:
        return {
            "job_id": job_id,
            "result": result
        }

    return {
        "status": "pending"
    }


@app.get("/status/{job_id}")
def job_status(job_id: str):

    status = get_status(job_id)

    if status:
        return {
            "job_id": job_id,
            "status": status
        }

    return {
        "status": "unknown"
    }    


# @app.get("/metrics")
# def metrics():

#     queue_length = get_queue_length()
#     completed = get_completed()

#     return {
#         "queue_length": queue_length,
#         "jobs_completed": completed
#     }


@app.get("/metrics")
def prometheus_metrics():

    queue_length = get_queue_length()

    queue_gauge.set(queue_length)

    return Response(
        generate_latest(),
        media_type="text/plain"
    )