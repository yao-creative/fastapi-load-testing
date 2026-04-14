# Celery + Redis Overview

Date: 2026-04-14

Goal: build the right runtime mental model before implementing anything.

This tutorial track is organized like this:

- `00` is the overview.
- `01` is a beginner architecture checkpoint.
- `02` through `09` are the actual exercises and interview-style prompts.
- The API file for this track is intentionally left unimplemented so you can fill it in yourself later from the docs.

If you do not yet have a clear picture of broker, worker, backend, and API boundaries, stop after `01` and make that mental model boringly clear first. That confusion will compound later in retries, routing, and observability.


## Runtime model

```text
Client
 └ HTTP request
    └ FastAPI app
       └ publishes Celery task message
          └ Redis broker
             └ Celery worker process
                └ task execution
                   └ Redis result backend
                      └ later poll / callback / downstream update
```

Important hierarchy:

- The API process and the worker process are different execution systems.
- Redis as broker is not the same concern as Redis as result backend.
- `celery beat` publishes scheduled tasks. Workers execute them.
- Retries mean the task body may run more than once.
- Idempotency matters as soon as retries or redelivery exist.

Beginner shortcut:

- API process: accepts the request and publishes a task.
- Worker process: actually runs the task code.
- Redis broker: holds queued work.
- Redis result backend: holds task status and result.


## Sequence diagrams

### Submit now, execute later, poll later

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Broker as Redis broker
    participant Worker as Celery worker
    participant Backend as Redis result backend

    Client->>API: POST /jobs
    API->>Broker: publish task
    API-->>Client: 202 Accepted + task_id
    Worker->>Broker: reserve task
    Worker->>Worker: execute task body
    Worker->>Backend: write task state/result
    Client->>API: GET /jobs/{task_id}
    API->>Backend: fetch state/result
    API-->>Client: PENDING / STARTED / SUCCESS / FAILURE
```

### Retry on transient failure

```mermaid
sequenceDiagram
    participant Worker
    participant Task
    participant Dependency as external dependency
    participant Broker as Redis broker

    Worker->>Task: run task
    Task->>Dependency: call dependency
    Dependency-->>Task: transient failure
    Task-->>Worker: retry
    Worker->>Broker: requeue task for later
    Broker-->>Worker: deliver task again
    Worker->>Task: rerun task body
```

### Fan-out / fan-in

```mermaid
sequenceDiagram
    participant API
    participant Broker
    participant W1 as worker 1
    participant W2 as worker 2
    participant W3 as worker 3
    participant Callback

    API->>Broker: publish group/chord
    par child tasks
        W1->>W1: child task A
    and
        W2->>W2: child task B
    and
        W3->>W3: child task C
    end
    Broker->>Callback: enqueue callback after all finish
```


## Where this shows up in frontier labs and companies

- Document ingestion: parse, OCR, metadata extraction, chunking, embedding, indexing.
- Benchmark and eval runs: schedule long-running evaluations, poll progress later.
- Batch media or report generation: accept work quickly, finish it out of band.
- Mixed-workload platforms: route user-facing short jobs away from heavy backfills.
- Periodic maintenance: stale index refresh, expired job cleanup, scheduled checks.

If you understand the toy exercises in this track, you will recognize the same failure modes in larger AI and product systems:

- request handlers waiting too long
- retries without duplicate-safe side effects
- one noisy queue starving everything else
- no clear distinction between scheduler, broker, worker, and result store


## Suggested route scaffold

The matching study scaffold lives in [app/api/tutorials_celery_redis.py](/Users/yao/projects/fastapi-load-testing/app/api/tutorials_celery_redis.py#L1).

Suggested route order:

1. `POST /tutorials/celery-redis/jobs/submit`
2. `GET /tutorials/celery-redis/jobs/{task_id}`
3. `POST /tutorials/celery-redis/jobs/retry-demo`
4. `POST /tutorials/celery-redis/jobs/progress-demo`
5. `POST /tutorials/celery-redis/jobs/fanout`
6. `GET /tutorials/celery-redis/queues/stats`
7. `POST /tutorials/celery-redis/beat/tick`
8. `POST /tutorials/celery-redis/streams/compare`

Suggested learning order:

1. `00-overview.md`
2. `01-what-runs-where.md`
3. `02-submit-and-poll.md`
4. `03-retries-and-idempotency.md`
5. `04-progress-reporting.md`
6. `05-fanout-and-fanin.md`
7. `06-queue-routing-and-isolation.md`
8. `07-periodic-jobs-and-beat.md`
9. `08-observability-and-failure-diagnosis.md`
10. `09-celery-vs-redis-streams.md`


## Official references

- Celery first steps: https://docs.celeryq.dev/en/stable/getting-started/first-steps-with-celery.html
- Celery tasks: https://docs.celeryq.dev/en/stable/userguide/tasks.html
- Celery calling API: https://docs.celeryq.dev/en/stable/userguide/calling.html
- Celery canvas: https://docs.celeryq.dev/en/stable/userguide/canvas.html
- Celery periodic tasks: https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
- Celery routing: https://docs.celeryq.dev/en/stable/userguide/routing.html
- Celery monitoring: https://docs.celeryq.dev/en/stable/userguide/monitoring.html
- Redis lists: https://redis.io/docs/latest/develop/data-types/lists/
- Redis streams: https://redis.io/docs/latest/develop/data-types/streams/


## Suggested folder organization and setup

Before implementing any of the exercises, set up the project shape you expect to grow into.

Suggested layout:

```text
app/
 ├ api/
 │  ├ tutorials_async.py
 │  └ tutorials_celery_redis.py
 ├ core/
 │  ├ celery_app.py
 │  ├ config.py
 │  └ logging.py
 ├ tasks/
 │  ├ jobs.py
 │  ├ pipelines.py
 │  └ periodic.py
 └ workers/
    └ __init__.py
docs/
 └ tutorials/
    └ celery-redis/
       ├ 00-overview.md
       ├ 01-what-runs-where.md
       ├ 02-submit-and-poll.md
       ├ 03-retries-and-idempotency.md
       └ ...
docker-compose.yml
```

What each area is for:

- `app/api/`: FastAPI routes that submit work or expose status.
- `app/core/celery_app.py`: Celery app construction, broker URL, backend URL, queue config.
- `app/tasks/`: task functions and workflow primitives.
- `app/workers/`: worker-specific bootstrap or imports if you want a dedicated worker entrypoint.
- `docs/tutorials/celery-redis/`: the learning track and implementation sequence.

Suggested setup order:

1. Create the doc files and the comment-form router first.
2. Add `app/core/celery_app.py`.
3. Add one small task module in `app/tasks/`.
4. Add Redis and worker services in `docker-compose.yml`.
5. Complete `01-what-runs-where` as a naming and architecture exercise.
6. Only then implement `02-submit-and-poll`.

This belongs in `00` because folder shape is part of the overview, not a later exercise.
