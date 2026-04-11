## Asyncio / FastAPI Leveling Rubric

Date: 2026-04-10

Goal: give a practical rubric for judging your current level on async Python backend work, based on what you can reason about, implement, debug, and explain under load.

This rubric is intentionally scoped to the topics in this repo:
- event loop behavior
- blocking vs yielding
- tasks, coroutines, threads, and workers
- fan-out and bounded concurrency
- timeouts, cancellation, and failure propagation
- shared-state correctness and backpressure


```
Need to fan out within one request?
  → asyncio.gather() or TaskGroup

Need structured fan-out with clean exception handling?
  → TaskGroup (Python 3.11+) — cancels siblings on first failure

Need to limit concurrency to protect downstream?
  → asyncio.Semaphore

Need producer/consumer or background draining?
  → asyncio.Queue + worker pool

Have blocking I/O (legacy sync lib, file read)?
  → asyncio.to_thread()

Have CPU-bound work that must be parallel?
  → ProcessPoolExecutor or separate service

Need more request throughput, not lower latency?
  → more Uvicorn workers (separate processes)
```

## How to use this rubric

Use the highest level where most statements are consistently true for you in practice, not just in theory.

Good signal:
- you can predict behavior before running the experiment
- you can explain why the result happened afterward
- you can implement the fix without cargo-culting

Weak signal:
- you recognize the vocabulary but still guess under pressure
- you know the “right words” but cannot instrument or verify behavior


## Junior

Typical signals:
- You can write `async def` and use `await`, but you still blur together coroutine, task, thread, and worker.
- You often assume async means “faster” without separating I/O-bound from CPU-bound work.
- You know blocking calls are bad in theory, but you may still accidentally put sync work inside async handlers.
- You can use `asyncio.gather(...)`, but you are not yet confident about its failure or cancellation behavior.
- You usually need guidance to choose between a simple await, a background task, a thread offload, or a queue.

What you can usually do:
- build a basic FastAPI async endpoint
- reproduce obvious blocking behavior
- follow an existing concurrency pattern

What you usually cannot do reliably yet:
- debug tail latency under mixed traffic
- explain why one worker behaves differently from many workers
- reason about backpressure or cancellation cleanup


## Mid-Level

Typical signals:
- You can clearly distinguish coroutine, task, thread, process, and Uvicorn worker.
- You can predict when async improves latency and when it does nothing.
- You know that `asyncio.gather(...)` improves one-request fan-out for yielding work, not CPU throughput.
- You know when to use `asyncio.to_thread(...)` and what problem it actually solves.
- You can explain why unbounded concurrency is risky and when to introduce a semaphore or queue.
- You can reason about one-request latency versus system throughput.
- You can instrument with request ids, timestamps, PIDs, and thread ids to validate a concurrency hypothesis.

What you can usually do:
- build correct async request handlers for ordinary I/O-heavy service work
- find accidental blocking calls in an async path
- implement bounded concurrency with `Semaphore`
- reason about per-process state under multiple Uvicorn workers
- explain basic timeout and cancellation behavior

What still limits you:
- complex failure propagation
- production overload behavior
- designing concurrency boundaries for teams, not just single endpoints


## Senior

Typical signals:
- You treat concurrency as a resource-management problem, not just a syntax feature.
- You can design stable limits for downstream dependencies and defend those limits with measurements.
- You understand cancellation, timeout boundaries, and cleanup well enough to avoid leaked work and corrupted state.
- You can compare `gather(...)`, `TaskGroup`, queues, semaphores, threads, and extra workers as architectural choices with tradeoffs.
- You can explain why a system is slow, overloaded, or unfair using instrumentation instead of intuition alone.
- You know how to choose between in-request work, in-process background work, and external job systems.
- You can review another engineer’s async design and point out failure modes before they show up in production.

What you can usually do:
- design and debug async services under realistic load
- tune concurrency limits for latency, throughput, and downstream safety
- build safe retry, timeout, and cancellation behavior
- design team-friendly patterns that avoid task leaks and overload collapse

What distinguishes you from strong mid-level:
- your decisions hold up in production
- your debugging is structured, not trial-and-error
- you think about correctness, fairness, overload, and observability together


## Staff+ Signals

This is beyond the scope of this repo, but the next jump usually looks like:
- setting service-wide concurrency standards
- designing platform defaults and guardrails
- choosing infrastructure patterns for many teams
- teaching others how to reason correctly about async failure modes


## Sample Tasks By Level

These are the kinds of tasks that separate levels more clearly than theory questions.

### Junior-level sample tasks

- Implement `/sleep/blocking` and `/sleep/async`, then explain why `/health` behaves differently under overlap.
- Implement `/fanout/sequential` and `/fanout/gather`, then compare end-to-end latency for one request.
- Add `os.getpid()` to responses and explain what it reveals when running with one worker versus two.

Expected evidence:
- correct code
- basic timing observations
- correct use of `await`

### Mid-level sample tasks

- Implement a bounded fan-out endpoint using `asyncio.Semaphore` and explain how capacity changes p95 latency.
- Add a timeout around a fan-out request and show which subtasks were cancelled versus completed.
- Reproduce a shared-state race in one process, then fix it with `asyncio.Lock`.
- Compare one worker versus two workers for two overlapping requests and explain the difference between per-request latency and total throughput.

Expected evidence:
- clear instrumentation
- correct conceptual explanation
- correct choice of primitive for the problem

### Senior-level sample tasks

- Design a request path that fans out to a fragile downstream dependency without overloading it under burst traffic.
- Compare `gather(...)` versus `TaskGroup` for a failure-sensitive workload and justify the choice.
- Define timeout budgets, cleanup behavior, and observability fields for a request that may partially complete work.
- Review an async endpoint that “works” in dev and identify the likely overload, fairness, and cancellation problems before load testing it.

Expected evidence:
- tradeoff reasoning
- failure-mode analysis
- stable limits and cleanup paths
- measurements tied back to design choices


## Self-Assessment Questions

If you can answer these without hand-waving, your understanding is becoming durable:

- Why does `await asyncio.sleep(...)` help concurrency, while `time.sleep(...)` blocks unrelated requests?
- Why can `asyncio.gather(...)` make one request much faster without using multiple workers?
- Why do more Uvicorn workers help throughput but not necessarily a single request?
- When does `asyncio.to_thread(...)` help, and what does it not solve?
- Why does unbounded fan-out create risk even if every subtask is “async”?
- What exactly does a semaphore protect you from?
- What does cancellation interrupt, and where must cleanup still run?
- Why can a single-threaded event loop still have race conditions?
- What changes when you move from one process to multiple workers?


## Self-Assessment Answer Key

Use these as signal checks. If your own answer is materially weaker than the one below, that topic is not stable yet.

### Why does `await asyncio.sleep(...)` help concurrency, while `time.sleep(...)` blocks unrelated requests?

Signal of a good answer:
- `await asyncio.sleep(...)` yields control back to the event loop, so other ready tasks can run on that worker while the current coroutine is waiting.
- `time.sleep(...)` blocks the worker thread itself, so the event loop cannot make progress on unrelated requests handled by that process.
- The core distinction is cooperative yielding versus blocking the thread.

### Why can `asyncio.gather(...)` make one request much faster without using multiple workers?

Signal of a good answer:
- `gather(...)` schedules multiple awaitable subtasks to make progress during the same request on the same event loop.
- If those subtasks mostly wait on timers or I/O, their wait times overlap.
- That changes one-request latency from roughly the sum of waits to roughly the longest wait plus overhead.
- This is intra-request concurrency, not multi-process parallelism.

### Why do more Uvicorn workers help throughput but not necessarily a single request?

Signal of a good answer:
- A Uvicorn worker is a separate process that handles whole requests.
- One incoming request is normally served by one worker process.
- More workers let multiple requests run in parallel across processes, which improves throughput and reduces queueing under concurrent traffic.
- They do not split one ordinary request across workers, so single-request latency often does not improve.

### When does `asyncio.to_thread(...)` help, and what does it not solve?

Signal of a good answer:
- `to_thread(...)` helps when code would otherwise block the event loop thread, such as sync I/O or blocking functions inside an async handler.
- It improves responsiveness because the event loop is no longer trapped inside that blocking call.
- It does not make pure Python CPU work scale like true parallel compute across cores in the general case.
- It is mainly a responsiveness and compatibility tool, not a universal performance upgrade.

### Why does unbounded fan-out create risk even if every subtask is “async”?

Signal of a good answer:
- Async subtasks still consume resources: sockets, DB connections, memory, downstream API quota, file descriptors, and scheduling overhead.
- If you start too many at once, you can overload a dependency, inflate tail latency, or create backlog collapse.
- Async removes blocking inefficiency; it does not remove capacity limits.

### What exactly does a semaphore protect you from?

Signal of a good answer:
- A semaphore limits how many coroutines can enter a critical section at the same time.
- It protects a scarce shared resource from excessive in-flight concurrency.
- The main win is stability and bounded pressure, not raw speed.
- In this repo’s context, it models things like DB pool slots or fragile downstream capacity.

### What does cancellation interrupt, and where must cleanup still run?

Signal of a good answer:
- Cancellation interrupts a coroutine by raising `CancelledError`, typically at an `await` boundary.
- Any held resource still has to be released in `finally` or equivalent cleanup paths.
- Good cleanup includes releasing semaphores, calling `task_done()`, closing clients, or recording terminal state.
- If cleanup is missing, timeouts and cancellations turn into leaks or deadlocks.

### Why can a single-threaded event loop still have race conditions?

Signal of a good answer:
- Race conditions are about unsafe interleaving, not only multiple OS threads.
- If coroutine A reads shared state, then yields, coroutine B can modify that state before A resumes.
- When A resumes and writes based on stale data, updates can be lost or state can become inconsistent.
- `asyncio.Lock` exists because coroutine-level interleaving is enough to create correctness bugs.

### What changes when you move from one process to multiple workers?

Signal of a good answer:
- Each worker is its own process with its own memory, event loop, queue, semaphore, and lock instances.
- In-memory state is no longer shared across workers unless you use an external system.
- Throughput and isolation improve because requests can run across processes.
- Per-process primitives like `asyncio.Lock` and `Semaphore` only coordinate work inside one worker, not across all workers.


## Recommended Practice Order In This Repo

1. `01-experiment-sleep-blocking-vs-async.md`
2. `02-experiment-cpu-inline-vs-to-thread.md`
3. `03-experiment-fanout-sequential-vs-gather.md`
4. `05-experiment-bounded-resource-semaphore.md`
5. `07-experiment-timeout-and-cancellation.md`
6. `08-experiment-gather-vs-taskgroup-failure-propagation.md`
7. `09-experiment-shared-state-race-and-lock.md`
8. `06-experiment-producer-consumer-asyncio-queue.md`

Why this order:
- Start with event-loop blocking and yielding.
- Then separate async waiting from CPU work.
- Then learn fan-out.
- Then learn to limit concurrency.
- Then learn to reason about failure, cancellation, and correctness.
- End with backpressure and queue-based coordination.


## Honest Interpretation

If you can implement and explain everything above cleanly, you are usually beyond “junior who has seen async before”.

Rough interpretation:
- Mostly junior tasks: junior
- Comfortable with most mid-level tasks: mid-level backend engineer
- Comfortable with most senior tasks and their tradeoffs: senior backend engineer

The decisive signal is not whether you know the terms. It is whether your mental model survives real experiments, debugging, and design review.
