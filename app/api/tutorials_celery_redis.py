from fastapi import APIRouter


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
#
# Suggested tutorial route sequence:
# 00. overview doc only, not an endpoint
# 01. POST /tutorials/celery-redis/jobs/submit
#     Learning goal: return 202 Accepted quickly and hand back a task id.
# 02. GET /tutorials/celery-redis/jobs/{task_id}
#     Learning goal: poll task state and understand result-backend reads.
# 03. POST /tutorials/celery-redis/jobs/retry-demo
#     Learning goal: model transient failure, retry, and idempotency.
# 04. POST /tutorials/celery-redis/jobs/progress-demo
#     Learning goal: expose stage-by-stage job progress.
# 05. POST /tutorials/celery-redis/jobs/fanout
#     Learning goal: model group / chord style fan-out and fan-in.
# 06. POST /tutorials/celery-redis/beat/tick
#     Learning goal: understand scheduler publish versus worker execution.
# 07. GET /tutorials/celery-redis/queues/stats
#     Learning goal: inspect queue depth, worker ownership, and backlog.
# 08. POST /tutorials/celery-redis/streams/compare
#     Learning goal: explain when Redis Streams fit better than Celery tasks.
#
# Suggested implementation guide:
# - Start with the 202 submit + poll-status pair.
# - Keep the first version deliberately small: one queue, one fake task body,
#   and a minimal status model.
# - Only after that add retries, progress updates, and routed queues.
# - If you later choose to add a real Celery stack, keep the route contract
#   stable so the docs and the exercise sequence still match.
