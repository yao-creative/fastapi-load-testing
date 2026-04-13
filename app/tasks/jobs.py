"""
Small job-oriented tasks.

Suggested first tasks to add here:

- a submit-and-poll demo task for `01`
- a retry/idempotency demo task for `02`
- a progress-reporting demo task for `03`
"""
import time

from app.core.celery_app import celery_app


# TODO(01): add one tiny task that simulates background work and returns a result.
@celery_app.task
def simulate_background_work(duration_ms: int):
    time.sleep(duration_ms / 1000)
    return "done"




# TODO(02): add one task that can fail transiently and retry.
# TODO(03): add one task that updates progress metadata by stage.
# TODO: keep "single task" exercises here; put multi-task workflows in `pipelines.py`.
