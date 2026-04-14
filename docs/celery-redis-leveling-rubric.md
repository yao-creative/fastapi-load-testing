## Celery + Redis Leveling Rubric

Date: 2026-04-12

Goal: give a practical rubric for judging your current level on Celery + Redis backend work, based on what you can reason about, implement, debug, and explain under failure, queueing, and production load.

This rubric is intentionally scoped to the topics in this repo:
- API request versus worker execution boundaries
- Redis as broker versus result backend
- submit-and-poll job patterns
- retries and idempotency
- fan-out / fan-in workflows
- queue routing and workload isolation
- periodic scheduling with beat
- observability, backlog, and failure diagnosis


```
Need to return quickly from an HTTP request?
  → submit task, return 202 Accepted, poll later

Need to survive transient downstream failure?
  → retry with idempotent side effects

Need visible long-running job stages?
  → update task state / progress metadata

Need parallel child work plus final aggregation?
  → group / chord style fan-out and fan-in

Need isolation between small and heavy jobs?
  → separate queues + dedicated workers

Need recurring maintenance or refresh work?
  → celery beat publishes, workers execute

Need “run this task later” semantics?
  → Celery

Need append-only event-log / consumer-group semantics?
  → Redis Streams, not just Celery
```

## How to use this rubric

Use the highest level where most statements are consistently true for you in practice, not just in theory.

Good signal:
- you can predict queueing and retry behavior before running the system
- you can explain failures in terms of broker, worker, result backend, and dependency boundaries
- you can design route contracts and task contracts that stay stable as the system grows

Weak signal:
- you know Celery vocabulary but still blur scheduler, broker, worker, and result backend together
- you can make a demo work but cannot explain duplicate execution, backlog, or failure recovery


## Junior

Typical signals:
- You understand the basic idea of background jobs, but still treat Celery as “FastAPI but later.”
- You know that long-running work should leave the request path, but you may not know what shape the API contract should take.
- You can submit a task and poll for status, but retries and duplicate side effects still feel hazy.
- You know Redis is involved, but you may still blur together broker, queue, result backend, and database.
- You can follow an example of `delay()` or `apply_async()`, but you are not yet confident about routing, beat, or workflow primitives.

What you can usually do:
- build a basic submit-and-poll flow
- explain why `202 Accepted` often makes more sense than waiting for completion
- follow an existing Celery setup for one queue and one worker

What you usually cannot do reliably yet:
- design safe retry behavior
- explain how duplicate execution happens
- debug backlog growth or queue starvation
- design clean queue boundaries for mixed workloads


## Mid-Level

Typical signals:
- You can clearly distinguish API process, broker, worker, beat, and result backend.
- You know the difference between task submission, task execution, and task state retrieval.
- You can explain retries as redelivery or re-execution attempts, not as continuation of one Python stack.
- You know that idempotency is required once retries or worker crashes enter the picture.
- You can describe when to use separate queues for light versus heavy work.
- You can implement progress reporting and reason about what metadata is worth exposing.
- You can explain `group`, `chain`, and `chord` at a practical level for document or batch workflows.

What you can usually do:
- design correct request/worker boundaries for ordinary product systems
- implement retries for transient failures without obvious duplicate side effects
- route work across multiple queues
- explain how beat fits into recurring task execution
- inspect queue backlog and task state to validate a hypothesis

What still limits you:
- overload behavior in production
- failure-mode design for larger workflows
- choosing between Celery and other queue or event primitives across teams


## Senior

Typical signals:
- You treat Celery as an operational system, not just a task decorator.
- You design idempotency, routing, queue ownership, and result retention on purpose.
- You can explain why a system is slow or unstable using queue depth, worker saturation, dependency failure, and retry pressure.
- You can compare one queue versus multiple queues, one worker pool versus dedicated pools, and one task versus a workflow with concrete tradeoffs.
- You know when Celery is the wrong abstraction and can defend a different design such as Redis Streams or a more explicit workflow engine.
- You review route and task contracts for failure modes before they hurt production.
- You think about observability, fairness, and backlog growth together instead of as separate issues.

What you can usually do:
- design and debug real background-job systems under mixed workload conditions
- build duplicate-safe retry behavior around unreliable dependencies
- create queue topologies that match business priorities
- choose which work belongs in request path, Celery, periodic jobs, or another subsystem
- define task contracts that other engineers can use safely

What distinguishes you from strong mid-level:
- your designs survive worker crashes, retries, and backlog pressure
- your debugging is systems-oriented rather than trial-and-error
- you can simplify queue architecture instead of only adding more moving parts


## Staff+ Signals

This is beyond the scope of this repo, but the next jump usually looks like:
- defining platform-wide job conventions and queue ownership
- standardizing retry, idempotency, and observability rules across teams
- choosing when to keep Celery, when to add Streams, and when to adopt a workflow engine
- teaching other engineers how to reason about backlog, duplication, and operational safety


## Sample Tasks By Level

These are the tasks that separate levels more clearly than vocabulary questions.

### Junior-level sample tasks

- Design `POST /jobs` and `GET /jobs/{task_id}` and explain why the result should not be waited on inline in the request.
- Explain what Redis is doing as broker and what it is doing as result backend.
- Add one tiny background task and describe the lifecycle from HTTP request to worker completion.

Expected evidence:
- correct API contract
- correct distinction between submit and execute
- basic understanding of task states

### Mid-level sample tasks

- Design a retryable task that calls a flaky dependency and explain how you prevent duplicate side effects.
- Split one mixed workload into `light` and `heavy` queues and justify the routing.
- Explain how you would represent progress for a multi-stage job.
- Design a fan-out / fan-in workflow for a document pipeline using child tasks plus a final aggregation step.

Expected evidence:
- correct retry reasoning
- correct idempotency reasoning
- useful task metadata and queue boundaries
- practical use of Celery workflow primitives

### Senior-level sample tasks

- Review a Celery system where queue depth is growing and explain the most likely causes and first debugging steps.
- Design queue topology and worker ownership for a product that has user-facing short jobs and large background backfills.
- Define a retry policy, idempotency key strategy, and result-retention policy for an unreliable downstream integration.
- Explain when a workload should move from Celery tasks to Redis Streams or another workflow abstraction.

Expected evidence:
- systems reasoning
- failure-mode analysis
- strong boundaries and operational judgment
- tradeoff-based architecture decisions


## Self-Assessment Questions

If you can answer these without hand-waving, your understanding is becoming durable:

- Why should an API usually return `202 Accepted` instead of waiting for long background work to finish?
- What is the difference between Redis as broker and Redis as result backend?
- Why do retries immediately force you to care about idempotency?
- Why is one default queue often enough for a demo and not enough for a real mixed workload?
- What problem does `celery beat` solve, and what problem does it not solve?
- What is the practical difference between one task and one workflow?
- When is Celery the right tool, and when are Redis Streams the better primitive?
- What signals tell you a queueing system is overloaded versus just temporarily busy?


## Self-Assessment Answer Key

Use these as signal checks. If your own answer is materially weaker than the one below, that topic is not stable yet.

### Why should an API usually return `202 Accepted` instead of waiting for long background work to finish?

Signal of a good answer:
- The request path should stay short and predictable.
- Long-running, failure-prone, or bursty work belongs in workers where retries and concurrency can be controlled separately.
- Returning `202 Accepted` plus a task id makes the API contract explicit: accepted now, completed later.

### What is the difference between Redis as broker and Redis as result backend?

Signal of a good answer:
- As broker, Redis holds queued task messages for workers to consume.
- As result backend, Redis stores task state and result metadata for later lookup.
- These are different responsibilities even if the same Redis deployment handles both.

### Why do retries immediately force you to care about idempotency?

Signal of a good answer:
- A retry means the task body may run again after partial progress, worker failure, timeout, or transient dependency error.
- If the side effect is not duplicate-safe, retries can send duplicate emails, create duplicate writes, or corrupt downstream state.
- The important key is usually a business idempotency key, not just the Celery task id.

### Why is one default queue often enough for a demo and not enough for a real mixed workload?

Signal of a good answer:
- A single queue is simple and fine when task duration and priority are similar.
- Once you mix short user-facing work with heavy backfills, long tasks can starve short tasks.
- Separate queues and workers create workload isolation and clearer ownership.

### What problem does `celery beat` solve, and what problem does it not solve?

Signal of a good answer:
- Beat solves scheduling of recurring task publication.
- It does not execute the task body itself.
- Workers still need to be healthy to consume and complete the scheduled work.

### What is the practical difference between one task and one workflow?

Signal of a good answer:
- One task is one unit of execution.
- A workflow coordinates multiple tasks, often with dependencies, fan-out, fan-in, or callbacks.
- Real product systems often need workflows, not just isolated tasks.

### When is Celery the right tool, and when are Redis Streams the better primitive?

Signal of a good answer:
- Celery is a strong fit for “run this background job” semantics, retries, scheduled work, and worker execution.
- Redis Streams are a better fit for append-only event processing, consumer groups, replay, and pending-entry management.
- A mature system may use Celery for jobs and Streams for event pipelines.

### What signals tell you a queueing system is overloaded versus just temporarily busy?

Signal of a good answer:
- Overload shows up as sustained queue growth, retry pressure, worker saturation, or growing completion latency.
- Temporary busy periods recover quickly once the burst passes.
- The key is trend and recovery behavior, not one high point in isolation.


## Recommended Practice Order In This Repo

1. `docs/tutorials/celery-redis/00-overview.md`
2. `docs/tutorials/celery-redis/01-what-runs-where.md`
3. `docs/tutorials/celery-redis/02-submit-and-poll.md`
4. `docs/tutorials/celery-redis/03-retries-and-idempotency.md`
5. `docs/tutorials/celery-redis/04-progress-reporting.md`
6. `docs/tutorials/celery-redis/05-fanout-and-fanin.md`
7. `docs/tutorials/celery-redis/06-queue-routing-and-isolation.md`
8. `docs/tutorials/celery-redis/07-periodic-jobs-and-beat.md`
9. `docs/tutorials/celery-redis/08-observability-and-failure-diagnosis.md`
10. `docs/tutorials/celery-redis/09-celery-vs-redis-streams.md`

Why this order:
- Start with execution boundaries and the basic runtime map.
- Then learn the API contract shape.
- Then learn safe retries and duplicate protection.
- Then add progress and workflow structure.
- Then learn workload isolation and recurring jobs.
- End with debugging and tool-choice judgment.


## Honest Interpretation

If you can implement and explain everything above cleanly, you are usually beyond “engineer who has used Celery once.”

Rough interpretation:
- Mostly junior tasks: junior
- Comfortable with most mid-level tasks: mid-level backend engineer
- Comfortable with most senior tasks and their tradeoffs: senior backend engineer

The decisive signal is not whether you know the Celery words. It is whether your mental model survives retries, duplication risk, backlog growth, and production debugging.
