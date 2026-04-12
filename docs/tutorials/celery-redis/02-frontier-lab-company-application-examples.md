# Celery + Redis Application Examples for Frontier Labs and Companies

Date: 2026-04-12

Goal: connect each Celery + Redis pattern in this tutorial track to the kinds of systems that appear in AI labs, model-platform teams, and product companies that run long-lived background workloads.

This file is not claiming that every frontier lab or company uses this exact stack.
The point is narrower:

- these Celery + Redis patterns map very directly to common production workload shapes
- if you understand the toy version, you can usually recognize the same pressure in a larger AI or product system


## 00: Celery + Redis sequence diagrams

File:

- `docs/tutorials/celery-redis/00-celery-redis-sequence-diagrams.md`

Real-world analogs:

- an API accepts a dataset ingestion request, returns quickly, and the heavy work continues in a worker fleet
- an internal tool triggers a long-running evaluation or report-generation job
- a platform service publishes background work into separate queues for different execution classes

Why this maps:

- background execution is the normal shape whenever the work is too slow, too failure-prone, or too bursty for the request path
- AI systems routinely have parse, transform, fetch, score, and store stages that do not belong inside one live HTTP request

Sample code sketch:

```python
@app.post("/eval-runs")
async def create_eval_run(dataset_id: str):
    task = run_eval.apply_async(kwargs={"dataset_id": dataset_id})
    return {
        "status": "accepted",
        "task_id": task.id,
        "status_url": f"/eval-runs/{task.id}",
    }
```


## 01: submit-job and poll-status

File:

- `docs/tutorials/celery-redis/01-high-roi-exercises.md`

Real-world analogs:

- document ingestion for retrieval or search systems
- long-running exports and compliance reports
- media generation, transcoding, or asset processing

What the lesson becomes in practice:

- the user-facing API should acknowledge work quickly
- the real work moves into workers where retries, queueing, and concurrency can be controlled separately

Sample code sketch:

```python
@app.get("/jobs/{task_id}")
async def get_job(task_id: str):
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "state": result.state,
        "result": result.result if result.successful() else None,
    }
```


## 02: retries and idempotency

File:

- `docs/tutorials/celery-redis/01-high-roi-exercises.md`

Real-world analogs:

- calling external LLM APIs, OCR vendors, vector databases, or webhook targets
- sending user notifications where duplicate delivery is costly
- updating downstream stores where a repeated write can corrupt business state

What the lesson becomes in practice:

- transient failures are normal
- duplicate-safe side effects are not optional once retries exist
- task design needs a business key, not just a Celery `task_id`

Sample code sketch:

```python
@celery_app.task(bind=True, autoretry_for=(TimeoutError,), retry_backoff=True)
def sync_embedding_batch(self, batch_id: str):
    if already_synced(batch_id):
        return {"status": "deduped"}
    vectors = fetch_vectors(batch_id)
    store_vectors(batch_id, vectors)
    mark_synced(batch_id)
    return {"status": "ok"}
```


## 03: progress reporting

File:

- `docs/tutorials/celery-redis/01-high-roi-exercises.md`

Real-world analogs:

- long document imports with visible stages
- benchmark runs with pass-by-pass progress
- multimodal preprocessing pipelines where users need visibility before completion

What the lesson becomes in practice:

- platform users want to know whether the job is queued, running, stuck, or partially complete
- stage-aware progress makes operator triage much easier than binary success/failure

Sample code sketch:

```python
@celery_app.task(bind=True)
def ingest_document(self, doc_id: str):
    self.update_state(state="PROGRESS", meta={"stage": "parse"})
    parsed = parse_document(doc_id)
    self.update_state(state="PROGRESS", meta={"stage": "embed"})
    embed_document(parsed)
    self.update_state(state="PROGRESS", meta={"stage": "index"})
    index_document(doc_id)
    return {"doc_id": doc_id, "status": "ready"}
```


## 04: fan-out / fan-in pipelines

File:

- `docs/tutorials/celery-redis/01-high-roi-exercises.md`

Real-world analogs:

- OCR, parsing, metadata extraction, and chunking over one uploaded corpus
- parallel safety or quality checks over many model outputs
- batch evaluation where each sample is scored independently and then aggregated

What the lesson becomes in practice:

- one request often needs many parallel task executions
- the callback or reducer stage is where the system becomes a workflow instead of a queue

Sample code sketch:

```python
header = group(
    parse_page.s(doc_id, page_no)
    for page_no in range(page_count)
)
workflow = chord(header)(finalize_document.s(doc_id))
```


## 05: routing and queue separation

File:

- `docs/tutorials/celery-redis/01-high-roi-exercises.md`

Real-world analogs:

- lightweight notification or bookkeeping jobs versus heavy ingestion jobs
- CPU-heavy preprocessing separated from latency-sensitive callback handling
- lower-priority batch work isolated from user-triggered tasks

What the lesson becomes in practice:

- queue design is an application-level admission-control policy
- if all workloads share one queue, noisy heavy work dominates everything else

Sample code sketch:

```python
notify_user.apply_async(kwargs={"user_id": user_id}, queue="light")
backfill_embeddings.apply_async(kwargs={"dataset_id": dataset_id}, queue="heavy")
```


## 06: periodic scheduling with beat

File:

- `docs/tutorials/celery-redis/01-high-roi-exercises.md`

Real-world analogs:

- scheduled benchmark suites
- stale-index refresh jobs
- cleanup of abandoned uploads, expired caches, or incomplete workflow records

What the lesson becomes in practice:

- recurring platform maintenance is background work too
- the scheduler and the executor should be thought about separately

Sample code sketch:

```python
celery_app.conf.beat_schedule = {
    "refresh-stale-indexes": {
        "task": "app.tasks.refresh_stale_indexes",
        "schedule": 300.0,
    }
}
```


## 07: observability and stuck-work diagnosis

File:

- `docs/tutorials/celery-redis/01-high-roi-exercises.md`

Real-world analogs:

- worker fleets where one queue quietly backs up
- jobs that keep retrying because of provider throttling
- long-running pipelines where operators need to know whether the problem is queueing, execution, or downstream dependency failure

What the lesson becomes in practice:

- background systems are operational systems
- if you cannot inspect active, scheduled, reserved, and failed tasks, you are mostly guessing


## 08: when Redis Streams are the better primitive

File:

- `docs/tutorials/celery-redis/01-high-roi-exercises.md`

Real-world analogs:

- telemetry ingestion, trace fan-out, agent event logs, and append-only operational event streams
- systems where you care about replay, consumer groups, and pending-entry recovery more than “run this task function”

What the lesson becomes in practice:

- Celery is task-centric
- Streams are event-log-centric
- larger AI systems often need both categories somewhere in the platform


## Practical reading of this tutorial track

If your target is AI platform or infra work, the most important mappings are:

1. submit-job/poll-status for long-running user-triggered work
2. retries plus idempotency for unreliable external dependencies
3. chord-style fan-out/fan-in for document and evaluation pipelines
4. routed queues for mixed workload isolation
5. periodic tasks for maintenance and refresh loops

That set covers a very large fraction of the background-job patterns that show up in serious product systems.


## References

- Celery tasks: https://docs.celeryq.dev/en/stable/userguide/tasks.html
- Celery canvas: https://docs.celeryq.dev/en/stable/userguide/canvas.html
- Celery routing: https://docs.celeryq.dev/en/stable/userguide/routing.html
- Celery periodic tasks: https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
- Celery monitoring: https://docs.celeryq.dev/en/stable/userguide/monitoring.html
- Redis streams: https://redis.io/docs/latest/develop/data-types/streams/
