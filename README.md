## fastapi-load-testing (bare minimum)

Minimal scaffolding:
- FastAPI app managed by `uv`
- Dockerized API
- Dockerized Locust runner + UI

Endpoint implementations for asyncio variations are intentionally left to you (see TODO comments in `app/main.py`).

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

- Open Locust UI at `http://localhost:8089`
- Host should be `http://api:8000`
- You can leave the Host field empty; compose sets `LOCUST_HOST=http://api:8000`

## Learning TODOs

Use this repo as a lab, not just a benchmark. The goal is to create visible contention, measure it, and connect what you observe back to the asyncio, ASGI, and worker-model concepts from the reference material.

### 1. FastAPI + asyncio best practices

- [ ] Implement `time.sleep(...)` and `await asyncio.sleep(...)` endpoints and compare latency under concurrent Locust users.
- [ ] Implement a CPU-heavy inline endpoint and compare it with `asyncio.to_thread(...)`.
- [ ] Implement a sync outbound HTTP call and compare it with an async outbound HTTP call.
- [ ] Add a bounded resource demo with `asyncio.Semaphore` and observe queueing once concurrency exceeds capacity.
- [ ] Record what happens to p50, p95, p99, throughput, and error rate when one endpoint blocks the loop.

Concepts to discover:
- FastAPI runs on an ASGI server, and the event loop is the shared scheduler for async work inside a worker.
- Async code is only non-blocking when it reaches real `await` points.
- A single blocking call in one request can delay unrelated requests handled by the same worker.
- Thread offloading can isolate blocking work, but it does not make that work natively async.

Core conflicts to test:
- Blocking sleep versus async sleep
- Inline CPU work versus `asyncio.to_thread(...)`
- Sync I/O client versus async I/O client
- Unbounded concurrency versus semaphore-limited concurrency

### 2. Asyncio architecture: event loop, tasks, futures

- [ ] Add one endpoint that awaits subtasks sequentially and one that runs the same subtasks with `asyncio.gather(...)`.
- [ ] Make each subtask include a controlled delay so the difference between sequential and concurrent scheduling is obvious.
- [ ] Add request logging with timestamps to see when each subtask starts and finishes.
- [ ] In scratch code, inspect which values are coroutine objects, which become scheduled tasks, and which results are only available after awaiting completion.
- [ ] Write down what actually changes when concurrency rises: scheduling, overlap, and queueing, not CPU parallelism.

Concepts to discover:
- Calling an `async def` function creates a coroutine object; it does not start executing immediately.
- A task is a coroutine scheduled on the event loop.
- Concurrency is cooperative progress across many waiting operations, not the same thing as parallel CPU execution.
- Asyncio is strong for I/O-bound overlap and weak for heavy CPU loops unless you move that work elsewhere.

Core conflicts to test:
- Sequential awaits versus `asyncio.gather(...)`
- Coroutine creation versus task scheduling
- High I/O overlap versus CPU-bound starvation
- Cheap context switching versus false assumptions about parallelism

### 3. Gunicorn + Uvicorn deployment model

- [ ] Run the same load profile with one Uvicorn worker and then with multiple Gunicorn-managed Uvicorn workers.
- [ ] Re-run the blocking sleep and CPU-inline experiments under multi-worker mode.
- [ ] Compare how much a single bad endpoint hurts the system with one worker versus several workers.
- [ ] Observe process-level effects: CPU usage, memory growth, startup time, and whether tail latency improves or average latency alone improves.
- [ ] Decide which bottlenecks are application-level and which bottlenecks are deployment-level.

Concepts to discover:
- More workers mean more processes, and each process has its own event loop.
- Extra workers reduce the blast radius of one blocked worker, but they do not fix blocking application code.
- ASGI application design and process-level deployment tuning solve different problems.
- Worker count is a tradeoff among throughput, latency, memory, isolation, and operational simplicity.

Core conflicts to test:
- One worker versus many workers
- Better app behavior versus merely more process isolation
- Throughput gains versus memory cost
- Tail-latency improvement versus unchanged root cause

## Suggested test matrix

- [ ] 1 user, low spawn rate, baseline latency
- [ ] 50-100 users hitting only `/sleep/blocking`
- [ ] 50-100 users hitting only `/sleep/async`
- [ ] Mixed traffic: one bad endpoint plus `/health` to observe cross-request interference
- [ ] Fan-out sequential versus gather under the same upstream delay
- [ ] Sync outbound HTTP versus async outbound HTTP to the same internal target
- [ ] Single worker versus multi-worker with the same Locust profile
- [ ] Semaphore capacity lower than concurrency to simulate a pool bottleneck

## What to write down after each run

- [ ] Which resource saturated first: event loop responsiveness, CPU, threadpool, upstream delay, or worker count
- [ ] Whether latency rose gradually or collapsed suddenly
- [ ] Whether the problem was caused by blocking, queueing, or CPU exhaustion
- [ ] Which concept from the reference material best explains the result
- [ ] What would actually fix the issue: async I/O, thread offload, more workers, a queue, or a redesign

## Reference Articles
1. https://www.techbuddies.io/2026/01/05/top-7-fastapi-asyncio-best-practices-for-non-blocking-web-apis/
2. https://dev.to/imsushant12/asyncio-architecture-in-python-event-loops-tasks-and-futures-explained-4pn3
3. https://medium.com/@iklobato/mastering-gunicorn-and-uvicorn-the-right-way-to-deploy-fastapi-applications-aaa06849841e
4. https://www.youtube.com/watch?v=esIEW0aEKqk
