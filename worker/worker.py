import time

from prometheus_client import Histogram

from shared.model import run_inference
from shared.queue import dequeue_job, dequeue_batch
from shared.status import set_status
from shared.storage import increment_completed, store_result


job_latency = Histogram(
    "job_processing_seconds",
    "Time spent processing jobs"
)


def worker_loop():

    print("=== Worker started ===", flush=True)

    while True:

        #print("Checking for job...", flush=True)

        job = dequeue_job()

        if job:

            job_id = job["job_id"]
            texts = job["texts"]

            print(
                f"Processing job {job_id}",
                flush=True
            )

            try:

                set_status(job_id, "RUNNING")

                with job_latency.time():

                    results = run_inference(texts)
                    
                    store_result(job_id, results)

                increment_completed()
                set_status(job_id, "COMPLETED")

            except Exception as e:

                print(e, flush=True)

                set_status(job_id, "FAILED")

            print(
                f"Results for {job_id}: {results}",
                flush=True
            )

        else:

            time.sleep(2)


if __name__ == "__main__":
    worker_loop()