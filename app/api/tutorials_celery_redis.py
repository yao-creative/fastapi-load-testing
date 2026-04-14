from typing import Any

from celery import Task
from celery.result import AsyncResult
from fastapi import APIRouter, Request

from app.core.celery_app import celery_app
from app.tasks.jobs import simulate_background_work, simulate_background_work_with_failure, simulate_background_work_with_progress

router = APIRouter(
    prefix="/tutorials/celery-redis",
    tags=["tutorials-celery-redis"],
)


def enqueue_job(task: Task, request: Request, *args: Any, **kwargs: Any) -> dict[str, str]:
    queued_task = task.delay(*args, **kwargs)
    return {
        "task_id": queued_task.id,
        "status": "PENDING",
        "poll_url": str(request.url_for("get_job", task_id=queued_task.id)),
    }


def extract_task_meta(task: AsyncResult) -> Any | None:
    if task.state == "PENDING":
        return None

    info = task.info
    if isinstance(info, Exception):
        return {"message": str(info)}

    return info


# Learning goal:
# Build the same kind of intuition for Celery + Redis that `tutorials_async.py`
# builds for asyncio:
# - what runs in the API process versus the worker process
# - what Redis is doing as broker and result backend
# - why request/response paths should stay short
# - where retries, idempotency, queue routing, and fan-in workflows matter
#
# Implementation policy for this file:
# Leave the exercises unimplemented on purpose. This file is a study scaffold,
# not the answer key. When you are ready to practice, add one route at a time.
# A useful rule of thumb:
# - API route submits or inspects work.
# - Celery worker executes work.
# - Redis broker carries task messages.
# - Redis result backend stores task state and result snapshots.
#
# Keep imports light here until the real stack exists. If `app/core/celery_app.py`
# or `app/tasks/*.py` are still missing, avoid adding placeholder calls that make
# the module fail at import time.
#
# Suggested tutorial route sequence:
# 00. overview doc only, not an endpoint
# 01. what-runs-where doc only, not an endpoint


# 02. POST /tutorials/celery-redis/jobs/submit
#     Learning goal: return 202 Accepted quickly and hand back a task id.
#     Sub-goals:
#     - keep the HTTP request short
#     - hand the client a stable task id
#     - make "submit now, poll later" feel normal
#     Suggested request shape:
#     - `duration_ms: int` for the toy version, or a small JSON body if you want
#       the task contract to resemble production code.
#     Suggested response shape:
#     - `{"task_id": "...", "status": "queued", "poll_url": "..."}`
#     Hints:
#     - Use `task.delay(...)` or `task.apply_async(...)`.
#     - Return `202 Accepted`, not `200`, because the work is not done yet.
#     - Do not wait for `.get()` inside the request handler.
#     - Log the task id at submit time so later poll/debug flows can correlate.

@router.post("/jobs/submit", status_code=202)
async def submit_job(duration_ms: int, request: Request):
    return enqueue_job(simulate_background_work, request, duration_ms)



# 02. GET /tutorials/celery-redis/jobs/{task_id}
#     Learning goal: poll task state and understand result-backend reads.
#     Sub-goals:
#     - read task state without rerunning the task
#     - distinguish queued, running, and finished states
#     - understand that poll reads shared state, not worker-local state
#     Suggested response shape:
#     - `{"task_id": "...", "state": "PENDING", "ready": false}`
#     - `{"task_id": "...", "state": "SUCCESS", "ready": true, "result": {...}}`
#     - `{"task_id": "...", "state": "FAILURE", "ready": true, "error": "..."}`
#     Hints:
#     - Look up the task via `AsyncResult(task_id, app=celery_app)`.
#     - Keep the poll route read-only; it should never trigger execution.
#     - Decide explicitly how to represent an unknown task id:
#       backend-only `PENDING`, synthetic `UNKNOWN`, or HTTP `404`.
#     - Make the first version small: state, readiness, result/error summary.
@router.get("/jobs/{task_id}", name="get_job")
async def get_job(task_id: str):
    task = AsyncResult(task_id, app=celery_app)
    response = {"task_id": task.id, "state": task.state, "ready": task.ready()}
    meta = extract_task_meta(task)

    if meta is not None:
        response["meta"] = meta

    if task.state == "SUCCESS":
        response["result"] = task.result
    elif task.state == "FAILURE":
        response["error"] = str(task.result)

    return response

# 03. POST /tutorials/celery-redis/jobs/retry-demo
#     Learning goal: model transient failure, retry, and idempotency.
#     Sub-goals:
#     - see that one task body may run more than once
#     - identify the duplicate-sensitive side effect
#     - protect that side effect with a business idempotency key
#     Suggested request shape:
#     - accept a business input like `business_id` once you move past the toy version
#     - force one deterministic transient failure so retry behavior is visible
#     Suggested response shape:
#     - immediate `202` with task id, plus a note that retries are expected
#     Hints:
#     - Learn retry first, then add idempotency on top.
#     - Put retry behavior in the task body, not in the API route.
#     - Make the side effect duplicate-safe before enabling retry.
#     - Persist or derive an idempotency key from business input, not just task id.
#     - Surface attempt count in logs or task metadata so the retry is visible.
@router.post("/jobs/retry-demo", status_code=202)
async def retry_demo(request: Request):
    return enqueue_job(
        simulate_background_work_with_failure,
        request,
        duration_ms=5000,
    )

# 04. POST /tutorials/celery-redis/jobs/progress-demo
#     Learning goal: expose stage-by-stage job progress.
#     Suggested progress model:
#     - `queued -> fetch -> process -> store -> success`
#     Hints:
#     - Use task state metadata for stage names and timestamps.
#     - Prefer stage labels over fake percentages unless the work is uniform.
#     - Preserve the current stage in failure output so the operator knows where
#       the task died.
@router.post("/jobs/progress-demo", status_code=202)
async def progress_demo(request: Request, fail_stage: str = None):
    return enqueue_job(
        simulate_background_work_with_progress,
        request,
        duration_ms=5000,
        fail_stage=fail_stage,
    )

# 05. POST /tutorials/celery-redis/jobs/fanout
#     Learning goal: model group / chord style fan-out and fan-in.
#     Suggested response shape:
#     - parent workflow id, child task ids, and a poll target for aggregate state.
#     Hints:
#     - Start with independent child tasks that return small deterministic values.
#     - Only add a chord callback after the child-result contract is stable.
#     - Decide how one-child failure affects the aggregate result before coding.


# 06. GET /tutorials/celery-redis/queues/stats
#     Learning goal: inspect queue depth, worker ownership, and backlog.
#     Suggested output:
#     - queue names, depth estimates, active workers, and a short interpretation.
#     Hints:
#     - Even mock stats are useful if the response shape teaches the right model.
#     - Separate "messages waiting" from "tasks currently executing".
#     - This route is for observability, not for mutating queue state.

# 07. POST /tutorials/celery-redis/beat/tick
#     Learning goal: understand scheduler publish versus worker execution.
#     Hints:
#     - If you implement this route, keep it educational: inspect schedule config,
#       trigger a one-off publish, or explain the next scheduled run.
#     - Do not blur beat and worker roles. Beat schedules; workers execute.
#     - Document what prevents overlapping scheduled runs.

# 08. POST /tutorials/celery-redis/streams/compare
#     Learning goal: explain when Redis Streams fit better than Celery tasks.
#     Suggested output:
#     - side-by-side comparison for task queue vs event-log workload.
#     Hints:
#     - Keep this route doc-like; a computed explanation payload is enough.
#     - Emphasize replay/history for Streams and workflow/task ergonomics for Celery.
#
# Suggested implementation guide:
# - Start with the 202 submit + poll-status pair.
# - Keep the first version deliberately small: one queue, one fake task body,
#   and a minimal status model.
# - Only after that add retries, progress updates, and routed queues.
# - If you later choose to add a real Celery stack, keep the route contract
#   stable so the docs and the exercise sequence still match.
#
# TODO map for this repo:
# - Edit `app/core/celery_app.py` when you are ready to construct the real Celery app.
# - Edit `app/core/config.py` when you want Redis URLs and queue names in one place.
# - Add first single-job tasks in `app/tasks/jobs.py`.
# - Add fan-out / fan-in workflows in `app/tasks/pipelines.py`.
# - Add scheduled jobs in `app/tasks/periodic.py`.
# - Add worker / beat bootstrap notes in `app/workers/`.
# - Add Redis / worker / beat services in `docker-compose.yml` after the doc-first pass.
