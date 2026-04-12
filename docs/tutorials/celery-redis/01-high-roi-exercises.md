# Celery + Redis: 8 High-ROI Exercises

Date: 2026-04-12

Goal: focus on the exercises that teach the most reusable Celery + Redis skills for web backends, internal tools, AI pipelines, and operations-heavy product work.

Recommended order:

1. Exercise 1 through 4 are the core model.
2. Exercise 5 and 6 are what usually make the system production-usable.
3. Exercise 7 and 8 are where your judgment gets sharper.

If time is limited, stop after Exercise 6.


## Exercise 1: FastAPI submits a job and returns `202 Accepted`

Why this is high ROI:

- This is the base pattern behind file ingestion, report generation, eval runs, and media processing.
- It forces you to separate request handling from background execution.

Build:

- `POST /jobs` publishes a Celery task with Redis as broker.
- Return `task_id` immediately.
- `GET /jobs/{task_id}` returns `PENDING`, `STARTED`, `SUCCESS`, or `FAILURE`.

Success criteria:

- The HTTP request returns quickly even when the task sleeps for 10 to 30 seconds.
- Worker logs clearly show that the task ran outside the FastAPI request process.

Stretch:

- Return `202 Accepted` with a status URL.
- Store your own job record table instead of trusting the result backend as your only system of record.


## Exercise 2: Retries plus idempotency for a flaky external dependency

Why this is high ROI:

- This is where most real systems become either robust or dangerous.
- Retries without duplicate-safe task design create double writes, double emails, double charges, or double indexing.

Build:

- Make a task that randomly fails about 30 to 50 percent of the time.
- Add retry with backoff.
- Add an idempotency key or dedupe record so the side effect happens at most once.

Success criteria:

- The task can be retried several times without producing duplicate business effects.
- Logs show attempt count, retry reason, and final outcome.

Stretch:

- Make the first side effect happen before the failure point so you can prove the idempotency guard works.


## Exercise 3: Progress reporting for a long-running task

Why this is high ROI:

- Users care less about raw background execution than about “what stage is it in?”
- This pattern shows up in imports, evaluations, backfills, and data-processing dashboards.

Build:

- Make one long task with 4 to 6 stages.
- Update task state or metadata after each stage.
- Expose that progress from `GET /jobs/{task_id}`.

Success criteria:

- You can see stage transitions such as `queued`, `started`, `fetching`, `processing`, `storing`, `done`.
- Failure responses include the stage where the task died.

Stretch:

- Add ETA estimates or processed item counts.


## Exercise 4: Fan-out / fan-in with `group` or `chord`

Why this is high ROI:

- This teaches the Celery primitive that most resembles real pipelines.
- It maps directly to document parsing, multi-source retrieval, safety sweeps, and batch evaluation.

Build:

- One parent request submits 5 to 20 child tasks.
- Use `group` if you only need all results back.
- Use `chord` if you want a callback task that merges or summarizes the children.

Success criteria:

- Child tasks run concurrently across workers.
- The final callback only runs after every child task succeeds.

Stretch:

- Make one child fail and decide what overall behavior you want.


## Exercise 5: Separate light and heavy queues

Why this is high ROI:

- A single default queue is fine for demos and bad for mixed workloads.
- This exercise teaches you how starvation appears and how routing fixes it.

Build:

- Create one queue for lightweight tasks such as notifications or webhook delivery.
- Create one queue for heavy tasks such as OCR, embeddings backfill, or archive processing.
- Start dedicated workers for each queue.

Success criteria:

- Heavy backlog does not materially delay the light queue.
- Worker startup commands and logs make queue ownership obvious.

Stretch:

- Add per-task rate limits or worker concurrency changes and observe queue behavior.


## Exercise 6: Periodic jobs with `celery beat`

Why this is high ROI:

- Most product systems need scheduled refreshes, cleanup, consistency sweeps, or recurring backfills.
- You need to understand that beat schedules and workers execute.

Build:

- Add `celery beat`.
- Schedule one minute-level job such as cleaning expired records, refreshing a derived index, or checking a stale-data table.

Success criteria:

- The task appears on schedule without an HTTP request triggering it.
- If workers are down, beat still publishes but nothing completes until workers return.

Stretch:

- Add a task lock so overlapping runs do not pile up.


## Exercise 7: Operational visibility with Flower and worker inspection

Why this is high ROI:

- Background systems fail silently unless you can see queue depth, active jobs, retries, and failures.
- This is usually the first operational gap in small teams.

Build:

- Run Flower.
- Inspect active, reserved, scheduled, and failed tasks while you trigger workloads.
- Capture screenshots or notes for one healthy run and one unhealthy run.

Success criteria:

- You can answer: what is running, what is stuck, what is retrying, and which queue is growing?
- You can correlate one `task_id` across API logs, worker logs, and monitoring.

Stretch:

- Intentionally kill a worker mid-task and record what happens next.


## Exercise 8: Contrast Celery queues with raw Redis Streams consumer groups

Why this is high ROI:

- This sharpens system design judgment.
- Celery is excellent for task execution workflows. Redis Streams teach you when you really want an event log and consumer-group semantics instead.

Build:

- Implement a tiny event ingestion pipeline using Redis Streams and a consumer group.
- Compare it to the same workload modeled as Celery tasks.

Success criteria:

- You can explain when Celery is the better tool and when Streams are the better primitive.
- You can describe acknowledgements, pending entries, replay, and multi-consumer processing at a practical level.

Stretch:

- Record the failure-handling differences between Celery retry and Streams pending-entry recovery.


## Suggested mini-capstone

Build one realistic pipeline after the exercises:

- `POST /documents` accepts an upload
- FastAPI stores a job record and publishes a Celery chord
- child tasks: parse, OCR, extract metadata, chunk
- callback task: merge outputs and mark the document ready
- periodic task: sweep stale jobs
- separate queues: `light`, `ingest`, `heavy`

If you can build that cleanly, you understand most of the Celery + Redis surface area that matters.


## Why these 8 made the cut

- They cover the core Celery docs surface you will actually reuse: tasks, calling, retries, canvas, routing, workers, monitoring, and periodic scheduling.
- They force you to handle failure modes instead of only happy-path syntax.
- They line up with common backend and AI-platform workloads better than toy arithmetic tasks.


## References

- Celery first steps: https://docs.celeryq.dev/en/stable/getting-started/first-steps-with-celery.html
- Celery tasks and retries: https://docs.celeryq.dev/en/stable/userguide/tasks.html
- Celery calling API: https://docs.celeryq.dev/en/stable/userguide/calling.html
- Celery canvas: https://docs.celeryq.dev/en/stable/userguide/canvas.html
- Celery periodic tasks: https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
- Celery routing tasks: https://docs.celeryq.dev/en/stable/userguide/routing.html
- Celery workers: https://docs.celeryq.dev/en/stable/userguide/workers.html
- Celery monitoring and management: https://docs.celeryq.dev/en/stable/userguide/monitoring.html
- Celery testing: https://docs.celeryq.dev/en/stable/userguide/testing.html
- Redis lists: https://redis.io/docs/latest/develop/data-types/lists/
- Redis streams: https://redis.io/docs/latest/develop/data-types/streams/
- FastAPI background tasks caveat: https://fastapi.tiangolo.com/tutorial/background-tasks/
