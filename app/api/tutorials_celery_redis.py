from fastapi import APIRouter
from celery.result import AsyncResult
from app.core.celery_app import celery_app
from app.tasks.jobs import simulate_background_work

router = APIRouter(
    prefix="/tutorials/celery-redis",
    tags=["tutorials-celery-redis"],
)


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


# 01. POST /tutorials/celery-redis/jobs/submit
#     Learning goal: return 202 Accepted quickly and hand back a task id.
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

@router.post("/jobs/submit")
async def submit_job(duration_ms: int):
    task = simulate_background_work.delay(duration_ms)
    return {"task_id": task.id, "status": "queued", "poll_url": f"/jobs/{task.id}"}

@router.get("/jobs/{task_id}")
async def get_job(task_id: str):
    task = AsyncResult(task_id, app=celery_app)
    return {"task_id": task.id, "state": task.state, "ready": task.ready()}

# 02. GET /tutorials/celery-redis/jobs/{task_id}
#     Learning goal: poll task state and understand result-backend reads.
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

# 03. POST /tutorials/celery-redis/jobs/retry-demo
#     Learning goal: model transient failure, retry, and idempotency.
#     Suggested request shape:
#     - force one deterministic transient failure so retry behavior is visible.
#     Suggested response shape:
#     - immediate `202` with task id, plus a note that retries are expected.
#     Hints:
#     - Put retry behavior in the task body, not in the API route.
#     - Make the side effect duplicate-safe before enabling retry.
#     - Persist or derive an idempotency key from business input, not just task id.
#     - Surface attempt count in logs or task metadata so the retry is visible.

# 04. POST /tutorials/celery-redis/jobs/progress-demo
#     Learning goal: expose stage-by-stage job progress.
#     Suggested progress model:
#     - `queued -> fetch -> process -> store -> success`
#     Hints:
#     - Use task state metadata for stage names and timestamps.
#     - Prefer stage labels over fake percentages unless the work is uniform.
#     - Preserve the current stage in failure output so the operator knows where
#       the task died.

# 05. POST /tutorials/celery-redis/jobs/fanout
#     Learning goal: model group / chord style fan-out and fan-in.
#     Suggested response shape:
#     - parent workflow id, child task ids, and a poll target for aggregate state.
#     Hints:
#     - Start with independent child tasks that return small deterministic values.
#     - Only add a chord callback after the child-result contract is stable.
#     - Decide how one-child failure affects the aggregate result before coding.

# 06. POST /tutorials/celery-redis/beat/tick
#     Learning goal: understand scheduler publish versus worker execution.
#     Hints:
#     - If you implement this route, keep it educational: inspect schedule config,
#       trigger a one-off publish, or explain the next scheduled run.
#     - Do not blur beat and worker roles. Beat schedules; workers execute.
#     - Document what prevents overlapping scheduled runs.

# 07. GET /tutorials/celery-redis/queues/stats
#     Learning goal: inspect queue depth, worker ownership, and backlog.
#     Suggested output:
#     - queue names, depth estimates, active workers, and a short interpretation.
#     Hints:
#     - Even mock stats are useful if the response shape teaches the right model.
#     - Separate "messages waiting" from "tasks currently executing".
#     - This route is for observability, not for mutating queue state.

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
#
# TODO(01):
# Add `POST /jobs/submit` and `GET /jobs/{task_id}` here.
# Start with one tiny task body, one queue, and a response contract that can stay
# stable after you switch from fake work to real work.
#
# TODO(02):
# Add a retry-demo route here only after `01` works cleanly.
# Prefer a deterministic "fail once, then succeed" exercise over random failure.
#
# TODO(03):
# Add a progress-demo route here after you decide what progress metadata looks like.
# Keep the metadata small: stage, attempt, started_at, updated_at.
#
# TODO(04):
# Add a fan-out / fan-in route here after you have at least one real child task.
# Avoid complex workflows until single-task submit/poll feels boring.
#
# TODO(06):
# Add a beat-trigger or schedule-inspection route here only if it improves learning.
# It is acceptable for this tutorial route to stay conceptual instead of executable.
