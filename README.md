# Async Concurrent Refresher

Async, Concurrent Refresher to rigorously check if I understand async concepts.

## fastapi-load-testing (bare minimum)

Minimal scaffolding:
- FastAPI app managed by `uv`
- Dockerized API
- Dockerized Locust runner + UI

The async tutorial endpoints are implemented in `app/api/tutorials_async.py`.

## Docs

- [docs/tutorials/async/00-asyncio-sequence-diagrams.md](docs/tutorials/async/00-asyncio-sequence-diagrams.md)
- [docs/tutorials/async/01-experiment-sleep-blocking-vs-async.md](docs/tutorials/async/01-experiment-sleep-blocking-vs-async.md)
- [docs/tutorials/async/02-experiment-cpu-inline-vs-to-thread.md](docs/tutorials/async/02-experiment-cpu-inline-vs-to-thread.md)
- [docs/tutorials/async/03-experiment-fanout-sequential-vs-gather.md](docs/tutorials/async/03-experiment-fanout-sequential-vs-gather.md)
- [docs/tutorials/async/04-experiment-timeout-and-cancellation.md](docs/tutorials/async/04-experiment-timeout-and-cancellation.md)
- [docs/tutorials/async/05-experiment-bounded-resource-semaphore.md](docs/tutorials/async/05-experiment-bounded-resource-semaphore.md)
- [docs/tutorials/async/06-experiment-producer-consumer-asyncio-queue.md](docs/tutorials/async/06-experiment-producer-consumer-asyncio-queue.md)
- [docs/tutorials/async/07-experiment-gather-vs-taskgroup-failure-propagation.md](docs/tutorials/async/07-experiment-gather-vs-taskgroup-failure-propagation.md)
- [docs/tutorials/async/08-experiment-shared-state-race-and-lock.md](docs/tutorials/async/08-experiment-shared-state-race-and-lock.md)
- [docs/frontier-ai-lab-application-examples.md](docs/frontier-ai-lab-application-examples.md)
- [docs/asyncio-leveling-rubric.md](docs/asyncio-leveling-rubric.md)
- [docs/tutorials/celery-redis/00-overview.md](docs/tutorials/celery-redis/00-overview.md)
- [docs/tutorials/celery-redis/01-submit-and-poll.md](docs/tutorials/celery-redis/01-submit-and-poll.md)
- [docs/tutorials/celery-redis/02-retries-and-idempotency.md](docs/tutorials/celery-redis/02-retries-and-idempotency.md)
- [docs/tutorials/celery-redis/03-progress-reporting.md](docs/tutorials/celery-redis/03-progress-reporting.md)
- [docs/tutorials/celery-redis/04-fanout-and-fanin.md](docs/tutorials/celery-redis/04-fanout-and-fanin.md)
- [docs/tutorials/celery-redis/05-queue-routing-and-isolation.md](docs/tutorials/celery-redis/05-queue-routing-and-isolation.md)
- [docs/tutorials/celery-redis/06-periodic-jobs-and-beat.md](docs/tutorials/celery-redis/06-periodic-jobs-and-beat.md)
- [docs/tutorials/celery-redis/07-observability-and-failure-diagnosis.md](docs/tutorials/celery-redis/07-observability-and-failure-diagnosis.md)
- [docs/tutorials/celery-redis/08-celery-vs-redis-streams.md](docs/tutorials/celery-redis/08-celery-vs-redis-streams.md)

## Local (uv)
- Install deps and create a venv:

```bash
uv sync
```

- Run the API:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Smoke test:

```bash
curl http://localhost:8000/health
```

- Open the generated OpenAPI UI to confirm methods and query params:

```bash
open http://localhost:8000/docs
```

## Calling The Async Tutorials

Most tutorial endpoints are `GET`. The queue lab is the exception:

```bash
curl -X POST "http://localhost:8000/tutorials/async/queue/enqueue?n=5&work_ms=250"
curl -X POST "http://localhost:8000/tutorials/async/queue/drain?n=5&work_ms=250"
curl "http://localhost:8000/tutorials/async/queue/stats"
```

If you call `/tutorials/async/queue/enqueue` or `/tutorials/async/queue/drain` without `-X POST`, FastAPI will return `405 Method Not Allowed`.
Under Docker, the API runs with `--workers 2`, so the in-memory queue runtime is per worker process. That means `/tutorials/async/queue/stats`, job IDs, and counters are not global across the whole service.

## Docker (API + Locust)
- Start API + Locust UI:

```bash
docker compose up --build --watch
```

- If the stack is already running and you only want to attach file watching:

```bash
docker compose watch
```

- Note: watch uses `sync+restart`, so changes under `./app` are pushed into the running container and the API container is restarted. Start with `docker compose up --build --watch` so the image and watched code begin from the same revision.
- Dependency or image changes in `pyproject.toml`, `uv.lock`, or `Dockerfile` trigger a rebuild automatically.

- Open Locust UI at `http://localhost:8089`
- Host should be `http://api:8000`
- You can leave the Host field empty; compose sets `LOCUST_HOST=http://api:8000`


## Reference Articles


1. https://www.techbuddies.io/2026/01/05/top-7-fastapi-asyncio-best-practices-for-non-blocking-web-apis/
2. https://dev.to/imsushant12/asyncio-architecture-in-python-event-loops-tasks-and-futures-explained-4pn3
3. https://medium.com/@iklobato/mastering-gunicorn-and-uvicorn-the-right-way-to-deploy-fastapi-applications-aaa06849841e
4. https://www.youtube.com/watch?v=esIEW0aEKqk
