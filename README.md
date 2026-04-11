# Async Concurrent Refresher

Async, Concurrent Refresher to rigorously check if I understand async concepts.

## fastapi-load-testing (bare minimum)

Minimal scaffolding:
- FastAPI app managed by `uv`
- Dockerized API
- Dockerized Locust runner + UI

Endpoint implementations for asyncio variations are intentionally left to you (see TODO comments in `app/main.py`).

## Docs

- [docs/tutorials/00-asyncio-sequence-diagrams.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/00-asyncio-sequence-diagrams.md)
- [docs/tutorials/01-experiment-sleep-blocking-vs-async.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/01-experiment-sleep-blocking-vs-async.md)
- [docs/tutorials/02-experiment-cpu-inline-vs-to-thread.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/02-experiment-cpu-inline-vs-to-thread.md)
- [docs/tutorials/03-experiment-fanout-sequential-vs-gather.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/03-experiment-fanout-sequential-vs-gather.md)
- [docs/tutorials/04-experiment-timeout-and-cancellation.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/04-experiment-timeout-and-cancellation.md)
- [docs/tutorials/05-experiment-bounded-resource-semaphore.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/05-experiment-bounded-resource-semaphore.md)
- [docs/tutorials/06-experiment-producer-consumer-asyncio-queue.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/06-experiment-producer-consumer-asyncio-queue.md)
- [docs/tutorials/07-experiment-gather-vs-taskgroup-failure-propagation.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/07-experiment-gather-vs-taskgroup-failure-propagation.md)
- [docs/tutorials/08-experiment-shared-state-race-and-lock.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/08-experiment-shared-state-race-and-lock.md)
- [docs/frontier-ai-lab-application-examples.md](/Users/yao/projects/fastapi-load-testing/docs/frontier-ai-lab-application-examples.md)
- [docs/asyncio-leveling-rubric.md](/Users/yao/projects/fastapi-load-testing/docs/asyncio-leveling-rubric.md)

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

## Docker (API + Locust)
- Start API + Locust UI:

```bash
docker compose up --build
```

- Start in dev mode with live code sync (Compose Watch):

```bash
docker compose watch
```

- Note: Watch is configured to **sync code and restart** the API container so changes apply while still running with **2 uvicorn workers** (it does not use `--reload`).

- Open Locust UI at `http://localhost:8089`
- Host should be `http://api:8000`
- You can leave the Host field empty; compose sets `LOCUST_HOST=http://api:8000`


## Reference Articles


1. https://www.techbuddies.io/2026/01/05/top-7-fastapi-asyncio-best-practices-for-non-blocking-web-apis/
2. https://dev.to/imsushant12/asyncio-architecture-in-python-event-loops-tasks-and-futures-explained-4pn3
3. https://medium.com/@iklobato/mastering-gunicorn-and-uvicorn-the-right-way-to-deploy-fastapi-applications-aaa06849841e
4. https://www.youtube.com/watch?v=esIEW0aEKqk
