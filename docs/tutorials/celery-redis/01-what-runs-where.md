# 01: What Runs Where

Date: 2026-04-14

Goal:

Build the smallest mental model first. Before writing retry logic or workflow code, be able to say which process is doing what.

Learning goals:

- know which code runs in the FastAPI process
- know which code runs in the Celery worker process
- know what Redis is doing in this tutorial
- know why the API can return before the task finishes

Sub-goals:

1. Separate request handling from background execution.
2. Separate Redis broker duties from Redis result-backend duties.
3. Recognize that a Celery task is not running inside the original HTTP request.

## Plain-English model

Use this sentence until it feels boring:

FastAPI accepts the request, Celery publishes a message, Redis holds that message, a worker picks it up later, and Redis stores task state so the API can poll it later.

## Runtime map

```text
Browser / curl
  -> FastAPI API process
     -> Celery client code inside the API process
        -> Redis broker stores task message
           -> Celery worker process reads message
              -> task function runs
                 -> Redis result backend stores state/result
                    -> FastAPI poll route reads state/result later
```

## What each piece is responsible for

- FastAPI route: accepts HTTP, validates input, submits work, returns quickly.
- Celery inside API: packages the task call and publishes it.
- Redis broker: temporary mailbox for queued tasks.
- Celery worker: separate process that actually runs the task body.
- Redis result backend: stores task state like `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`.

## What Redis means here

In this tutorial track, Redis has two jobs:

1. Broker: hold queued task messages until a worker consumes them.
2. Result backend: hold task state and final result so `/jobs/{task_id}` can read them later.

It is the same Redis server, but two different responsibilities.

## Quick checks

If you can answer these, you are ready for the next step:

- Does the task body run inside the `POST` request handler?
- If the API process dies after publishing but before polling, can the worker still run the task?
- Why can the client get `202 Accepted` before the work is done?
- Why is `GET /jobs/{task_id}` reading Redis instead of asking the worker directly?

## Small tasks

Do these before implementing anything harder:

1. Point to the file where the FastAPI route submits a task.
2. Point to the file where the task function actually runs.
3. Point to the place where broker/backend URLs are configured.
4. Explain in one sentence why `time.sleep()` inside a Celery task does not block the FastAPI request thread.

## Follow-up prompt

Explain this flow out loud without diagrams:

- client submits job
- API returns `202`
- worker starts later
- client polls later

If that explanation is still fuzzy, do not move to retries yet.
