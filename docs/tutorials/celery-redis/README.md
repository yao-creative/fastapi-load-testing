# Celery + Redis Tutorial Track

Date: 2026-04-12

Goal: learn the parts of Celery + Redis that actually matter in real systems:
- request-time job submission
- background worker execution
- retries and idempotency
- fan-out / fan-in workflows
- periodic scheduling
- routing, backpressure, and observability

Recommended reading order:

1. [00-celery-redis-sequence-diagrams.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/celery-redis/00-celery-redis-sequence-diagrams.md)
2. [01-high-roi-exercises.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/celery-redis/01-high-roi-exercises.md)
3. [02-frontier-lab-company-application-examples.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/celery-redis/02-frontier-lab-company-application-examples.md)

If you only do part of this track:

- Read `00` first so the runtime model is clear.
- Do Exercises 1 through 6 in `01`. That is the highest-return core.
- Read `02` last to connect the toy exercises to AI product and infrastructure workloads.

What this track is trying to teach:

- FastAPI should usually publish background work, not hold the request open for long jobs.
- Celery workers are a separate execution system from the web process.
- Redis can be the broker and the result backend, but that does not make it a full workflow engine.
- Retries, acknowledgements, and duplicate-safe task design matter more than “hello world” task syntax.
- Canvas primitives like `chain`, `group`, and `chord` matter because production jobs are usually pipelines, not single functions.
