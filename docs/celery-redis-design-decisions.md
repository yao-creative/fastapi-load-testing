# Celery + Redis Design Decisions

Date: 2026-04-12

Goal: make the common architecture choices around Celery + Redis explicit:

- when to keep work in the request path
- when to move work into Celery
- when Redis is enough
- when Redis Streams are the better primitive
- when you are outgrowing Celery and need a more explicit workflow system

This file is not claiming that every frontier lab or product company uses the same stack.
The point is narrower:

- these are the decision boundaries that show up repeatedly in AI platforms, internal tools, ingestion systems, and mixed-workload products
- if you understand the boundary well, you can usually choose the right tool before the system gets messy


## 1. First decision: request path or background job?

Keep work in the request path when:

- the user needs the result immediately
- the work is short and predictable
- the failure behavior is simple
- you can keep latency within a clear budget

Move work into Celery when:

- the work may take seconds or minutes
- the work is bursty and should queue
- the work may need retry
- the user can poll later or receive a callback later
- the work should not compete directly with latency-sensitive request handling

Bad shape:

```python
@app.post("/documents")
async def upload_document(file: UploadFile):
    parsed = parse_pdf(file.file.read())
    chunks = chunk_document(parsed)
    embeddings = await embed_chunks(chunks)
    await store_embeddings(embeddings)
    return {"status": "ready"}
```

Better shape:

```python
@app.post("/documents")
async def upload_document(file: UploadFile):
    doc_id = save_upload(file)
    task = ingest_document.delay(doc_id)
    return {"status": "accepted", "task_id": task.id, "doc_id": doc_id}
```


## 2. Celery versus in-process background work

Use in-process background work when:

- the task is very small
- losing the task on process restart is acceptable
- you do not need durable queueing
- you do not need worker fleets or multi-service scaling

Use Celery when:

- work must survive beyond one request process
- you want separate workers
- you need durable queueing semantics
- you need retries, routing, or scheduled execution

Practical rule:

- If the work is “a little bit later in the same service,” in-process background work may be enough.
- If the work is “a real job system,” use Celery or another external worker system.


## 3. Celery versus plain asyncio queues

Use `asyncio.Queue` when:

- the queue is explicitly per-process
- the exercise is about in-process coordination
- you do not need cross-process durability

Use Celery when:

- API and workers must be separate processes or containers
- you need persistent brokered work
- you want retries and worker routing
- you want the queue to outlive one app worker

Practical difference:

- `asyncio.Queue` is a local coordination primitive
- Celery is an external job-execution system


## 4. Redis as broker and result backend: when this is a good fit

Redis works well when:

- you want simple operational setup
- your task volume is moderate enough for Redis-backed queueing
- you want one fast system for broker and result metadata
- your team needs a practical starting point, not the most elaborate queue stack

Redis becomes uncomfortable when:

- you treat the result backend as your only business system of record
- retention and cleanup are ignored
- backlog, replay, and event-history requirements become more important than “run this task”
- many workload classes start competing in one loosely-managed Redis deployment

Good mental model:

- Redis broker: queued task messages
- Redis result backend: task state and result metadata
- Your own database: durable business state


## 5. Celery versus Redis Streams

Use Celery when the core question is:

- “How do I run this job later?”
- “How do I retry this task?”
- “How do I schedule this recurring maintenance job?”
- “How do I fan out background execution to workers?”

Use Redis Streams when the core question is:

- “How do I process this event log?”
- “How do multiple consumers coordinate over an append-only stream?”
- “How do I inspect pending entries and replay event consumption?”

Short version:

- Celery is task-centric
- Streams are event-log-centric

Example:

- “Generate embeddings for this uploaded document later” fits Celery
- “Consume a stream of agent tool events and build analytics” fits Streams


## 6. Celery versus a workflow engine

Celery is often enough when:

- workflows are short
- failure handling is understandable
- fan-out / fan-in is limited
- you do not need long-lived workflow history beyond task states

You may need a workflow engine when:

- workflows are long-lived and stateful
- compensation and recovery logic are complex
- humans or external approvals are part of the workflow
- replayable workflow history becomes a core requirement
- many teams are building interdependent workflows on one platform

Practical boundary:

- Celery is very good at jobs and modest workflows
- It is not automatically the right tool for every business process


## 7. Queue topology decisions

Start with one queue when:

- the system is small
- tasks are similar in duration and priority
- there is no meaningful distinction between user-facing short jobs and heavy offline work

Split into multiple queues when:

- short jobs are being delayed by heavy jobs
- different worker shapes or concurrency settings are needed
- the business priority of one workload is clearly higher than another

Common first split:

- `light`: notifications, callbacks, status updates, small transforms
- `heavy`: OCR, backfills, long parsing, batch indexing

Bad smell:

- “Everything goes on the default queue because we will clean it up later.”


## 8. Retry decisions

Retry when failure is likely transient:

- network timeout
- rate limit
- temporary dependency outage
- transient lock or resource contention

Do not blindly retry when failure is likely permanent:

- invalid payload
- schema violation
- missing required record
- business rule rejection

Design rule:

- retries require idempotency
- retries without idempotency are a correctness risk, not a resilience feature


## 9. Result backend decisions

Use the result backend for:

- task states
- progress metadata
- lightweight task outputs
- operator visibility

Do not lean on the result backend alone for:

- durable business records
- user-owned canonical state
- audit history that must outlive task retention windows

Design rule:

- task state is not the same thing as business state


## 10. Periodic scheduling decisions

Use beat when:

- work should happen on a schedule without an HTTP trigger
- maintenance or refresh work is recurring
- jobs should be queued in the same worker ecosystem as other tasks

Be careful when:

- a scheduled task can overlap with itself
- one recurring heavy job floods the same queue as user-facing work
- workers are down and scheduled tasks keep accumulating


## 11. Frontier lab and company examples

These are not claims about one exact vendor architecture. They are workload shapes that appear repeatedly in frontier labs, model-platform teams, and AI product companies.

### Example A: document ingestion pipeline

Use:

- Celery tasks
- heavy queue
- fan-out / fan-in

Why:

- parsing, OCR, metadata extraction, chunking, and indexing are naturally background work
- users usually do not need the result synchronously

Sample shape:

```python
@app.post("/documents")
async def create_document(file: UploadFile):
    doc_id = persist_upload(file)
    workflow = chord(
        [
            parse_document.s(doc_id),
            run_ocr.s(doc_id),
            extract_metadata.s(doc_id),
        ]
    )(finalize_document.s(doc_id))
    return {"status": "accepted", "workflow_id": workflow.id, "doc_id": doc_id}
```

### Example B: evaluation and benchmark runs

Use:

- Celery tasks
- submit-and-poll
- beat for recurring runs

Why:

- eval workloads are often long-running and batch-oriented
- users care about status and summary, not inline response latency

Sample shape:

```python
@app.post("/eval-runs")
async def create_eval_run(dataset_id: str):
    task = run_eval.delay(dataset_id)
    return {"status": "accepted", "task_id": task.id}
```

### Example C: mixed user-facing and offline workloads

Use:

- multiple queues
- dedicated workers

Why:

- user-triggered short tasks should not wait behind large backfills
- this is a common platform problem once AI products have both live usage and internal maintenance jobs

Sample shape:

```python
notify_user.apply_async(kwargs={"user_id": user_id}, queue="light")
backfill_embeddings.apply_async(kwargs={"dataset_id": dataset_id}, queue="heavy")
```

### Example D: recurring maintenance

Use:

- beat
- routed queues

Why:

- stale index refresh, abandoned upload cleanup, and scheduled consistency checks are all recurring background work

Sample shape:

```python
celery_app.conf.beat_schedule = {
    "refresh-stale-indexes": {
        "task": "app.tasks.periodic.refresh_stale_indexes",
        "schedule": 300.0,
    }
}
```

### Example E: event analytics and agent telemetry

Use:

- Redis Streams, not just Celery

Why:

- append-only event flow, replay, and consumer-group semantics matter more than “execute this job”

Sample shape:

```python
async def consume_agent_events():
    while True:
        events = await stream_client.read_group(
            group="analytics",
            consumer="worker-1",
            streams={"agent-events": ">"},
        )
        for event in events:
            await process_event(event)
```


## 12. Decision cheatsheet

If the question sounds like this:

- “Return fast and finish later” -> Celery submit-and-poll
- “Retry this flaky dependency safely” -> Celery + idempotency
- “Run many child jobs then merge results” -> Celery workflow primitives
- “Keep short jobs away from heavy jobs” -> multiple queues + dedicated workers
- “Run this every hour” -> beat
- “Process this event stream with replay and consumer groups” -> Redis Streams
- “Model a long-lived business workflow with richer state and compensation” -> consider a workflow engine


## 13. Best Practices

These are the defaults that keep small Celery + Redis systems from becoming unreliable too quickly.

### API contract

- Return `202 Accepted` for long-running work instead of waiting inline.
- Return a stable task id or job id that the client can poll later.
- Keep task state separate from business state; task completion alone should not be your only source of truth.

### Task design

- Make task side effects idempotent before enabling retries aggressively.
- Keep task inputs small and pass stable identifiers instead of large payload blobs when possible.
- Prefer explicit task arguments over hidden global state.
- Keep one task focused on one clear responsibility.

### Retry behavior

- Retry only transient failures.
- Do not blindly retry validation errors, bad payloads, or permanent business-rule failures.
- Record attempt count and failure reason in logs or task metadata.
- Use backoff so retries do not amplify dependency pressure.

### Queue design

- Start simple, but split queues once workload classes clearly differ.
- Keep short user-facing work away from heavy backfills or long parsing jobs.
- Make queue ownership obvious: engineers should know which workers consume which queues.

### Result backend and data ownership

- Use the result backend for task state, progress, and lightweight outputs.
- Store canonical business records in your database, not only in Celery result metadata.
- Set retention expectations early so result data does not grow without control.

### Observability

- Log task id, queue, attempt count, and the relevant business key.
- Track queue depth, completion latency, failure count, and retry count.
- Make it easy to correlate one user action with one submitted task and one worker execution path.

### Scheduling

- Treat beat as a publisher, not an executor.
- Decide whether scheduled jobs may overlap before adding them.
- Route heavy scheduled jobs away from user-facing queues if they compete for the same workers.

### Evolution path

- Start with submit-and-poll before adding chords, multiple queues, or beat.
- Add complexity only when the workload actually demands it.
- Revisit the abstraction when you start wanting event replay, richer workflow history, or complex compensation logic.


## Recommended reading alongside this file

- [docs/tutorials/celery-redis/00-overview.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/celery-redis/00-overview.md)
- [docs/tutorials/celery-redis/01-what-runs-where.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/celery-redis/01-what-runs-where.md)
- [docs/tutorials/celery-redis/02-submit-and-poll.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/celery-redis/02-submit-and-poll.md)
- [docs/tutorials/celery-redis/05-fanout-and-fanin.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/celery-redis/05-fanout-and-fanin.md)
- [docs/tutorials/celery-redis/06-queue-routing-and-isolation.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/celery-redis/06-queue-routing-and-isolation.md)
- [docs/tutorials/celery-redis/09-celery-vs-redis-streams.md](/Users/yao/projects/fastapi-load-testing/docs/tutorials/celery-redis/09-celery-vs-redis-streams.md)
- [docs/celery-redis-leveling-rubric.md](/Users/yao/projects/fastapi-load-testing/docs/celery-redis-leveling-rubric.md)
