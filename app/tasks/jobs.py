"""
Small job-oriented tasks.

Suggested first tasks to add here:

- a submit-and-poll demo task for `01`
- a retry/idempotency demo task for `02`
- a progress-reporting demo task for `03`
"""
import time

from app.core.celery_app import celery_app


# Router-tracked tutorial 01 job task: submit-and-poll.
@celery_app.task
def simulate_background_work(duration_ms: int):
    time.sleep(duration_ms / 1000)
    return {
        "status": "done",
        "stage": "success",
        "duration_ms": duration_ms,
    }

# Router-tracked tutorial 02 job task: retry demo.
@celery_app.task(bind=True, max_retries=3, default_retry_delay=1)
def simulate_background_work_with_failure(self, duration_ms: int):
    attempt = self.request.retries + 1
    transient_error = RuntimeError("Simulated transient failure")

    self.update_state(
        state="PROGRESS",
        meta={
            "stage": "attempting-work",
            "attempt": attempt,
            "max_retries": self.max_retries,
        },
    )

    time.sleep(duration_ms / 1000)

    if self.request.retries == 0:
        raise self.retry(exc=transient_error, countdown=1)

    return {
        "status": "done",
        "stage": "success-after-retry",
        "attempt": attempt,
        "duration_ms": duration_ms,
    }

# Router-tracked tutorial 03 job task: progress-reporting demo.
@celery_app.task(bind=True)
def simulate_background_work_with_progress(self, duration_ms: int):
    stages = [
        "fetching-input",
        "processing-data",
        "storing-output",
    ]
    step_duration_seconds = duration_ms / 1000

    for index, stage in enumerate(stages, start=1):
        self.update_state(
            state="PROGRESS",
            meta={
                "stage": stage,
                "current_step": index,
                "total_steps": len(stages),
                "progress_percent": int(index / len(stages) * 100),
            },
        )
        time.sleep(step_duration_seconds)

    return {
        "status": "done",
        "stage": "success",
        "total_steps": len(stages),
        "duration_ms": duration_ms,
    }

# TODO: keep "single task" exercises here; put multi-task workflows in `pipelines.py`.
