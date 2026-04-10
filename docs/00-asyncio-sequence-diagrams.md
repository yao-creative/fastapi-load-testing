# Asyncio Sequence Diagrams

Date: 2026-04-10

Goal: build an intuition for how `async` / `await`, coroutines, tasks, queues, workers, and related asyncio primitives behave at runtime.


```
CPU
 └ thread
    └ asyncio event loop
        ├ coroutine
        ├ coroutine
        └ coroutine
```


## 1. `async def` and `await`

Key idea:

- `async def` defines a coroutine function.
- Calling it creates a coroutine object.
- The coroutine does not make progress until the event loop runs it.
- `await` suspends the current coroutine and lets the event loop run something else.

```mermaid
sequenceDiagram
    participant C as Caller
    participant L as Event loop
    participant A as coroutine_a()
    participant B as coroutine_b()

    C->>A: call coroutine_a()
    Note over C,A: returns coroutine object
    C->>L: schedule coroutine_a
    L->>A: start running
    A->>B: await coroutine_b()
    Note over A: coroutine_a pauses here
    L->>B: run coroutine_b
    B-->>L: result
    L->>A: resume coroutine_a with result
    A-->>L: final result
    L-->>C: deliver result
```



## 2. Coroutine object versus Task

Key idea:

- A coroutine object is just a resumable computation.
- A `Task` is the event loop actively managing that coroutine.
- `asyncio.create_task(...)` turns a coroutine into scheduled concurrent work.

```mermaid
sequenceDiagram
    participant C as Caller
    participant L as Event loop
    participant Co as some_coro()
    participant T as Task

    C->>Co: some_coro()
    Note over Co: coroutine object created
    C->>L: asyncio.create_task(Co)
    L->>T: wrap coroutine in Task
    T->>Co: start / resume coroutine
    Co-->>T: await or return
    T-->>L: state updates managed by loop
    L-->>C: Task handle returned immediately
```



## 3. Awaiting directly versus creating a Task

Key idea:

- `await coro()` means "pause here until this finishes."
- `create_task(coro())` means "let this run concurrently while I keep going."

```mermaid
sequenceDiagram
    participant P as parent()
    participant L as Event loop
    participant C1 as child()
    participant T as Task(child)

    rect rgb(0, 0, 0)
        P->>C1: await child()
        Note over P: parent pauses immediately
        L->>C1: run child
        C1-->>P: result
    end

    rect rgb(0, 0, 0)
        P->>L: create_task(child())
        L->>T: schedule Task
        L-->>P: Task returned immediately
        Note over P: parent keeps running
        T->>T: child executes concurrently
    end
```



## 4. `asyncio.gather(...)` fan-out and fan-in

Key idea:

- `gather(...)` schedules multiple awaitables together.
- The caller suspends once, then resumes after all results are ready.

```mermaid
sequenceDiagram
    participant P as parent()
    participant L as Event loop
    participant A as fetch_a()
    participant B as fetch_b()
    participant G as gather(...)

    P->>G: await asyncio.gather(A, B)
    G->>L: schedule both coroutines
    L->>A: run fetch_a
    L->>B: run fetch_b
    A-->>G: result A
    B-->>G: result B
    G-->>P: [result A, result B]
```



## 5. Event loop interleaving at `await` points

Key idea:

- Async concurrency is cooperative.
- Switching happens when a coroutine awaits something that is not ready yet.
- If code never awaits, it can monopolize the loop.

```mermaid
sequenceDiagram
    participant L as Event loop
    participant T1 as task_1
    participant T2 as task_2
    participant IO as socket / timer

    L->>T1: resume task_1
    T1->>IO: await network read
    Note over T1: task_1 yields
    L->>T2: resume task_2
    T2->>IO: await sleep / I/O
    Note over T2: task_2 yields
    IO-->>L: task_1 ready
    L->>T1: resume task_1
    IO-->>L: task_2 ready
    L->>T2: resume task_2
```



## 6. Queue with producer and workers

Key idea:

- `asyncio.Queue` decouples producers from consumers.
- Producers `put(...)` work items into the queue.
- Worker tasks `get()` items, process them, then call `task_done()`.

```mermaid
sequenceDiagram
    participant P as Producer
    participant Q as asyncio.Queue
    participant W1 as Worker 1
    participant W2 as Worker 2

    P->>Q: put(job 1)
    P->>Q: put(job 2)
    P->>Q: put(job 3)
    W1->>Q: await get()
    Q-->>W1: job 1
    W2->>Q: await get()
    Q-->>W2: job 2
    W1->>W1: process job 1
    W2->>W2: process job 2
    W1->>Q: task_done()
    W1->>Q: await get()
    Q-->>W1: job 3
    W2->>Q: task_done()
    W1->>Q: task_done()
```



## 7. Waiting for a queue to drain with `queue.join()`

Key idea:

- `queue.join()` waits until every queued item has a matching `task_done()`.
- This is how a coordinator can wait for all enqueued work to finish.

```mermaid
sequenceDiagram
    participant M as Main coroutine
    participant Q as asyncio.Queue
    participant W as Worker task

    M->>Q: put(job 1..N)
    M->>Q: await queue.join()
    Note over M: main pauses until all jobs are marked done
    W->>Q: get job
    W->>W: process job
    W->>Q: task_done()
    Q-->>M: all unfinished tasks reached zero
    M->>W: cancel worker
```



## 8. Semaphore limiting concurrency

Key idea:

- A semaphore is a gate that limits how many coroutines may enter a critical section at once.
- This is useful for DB pools, rate-limited APIs, or bounded downstream capacity.

```mermaid
sequenceDiagram
    participant T1 as task_1
    participant T2 as task_2
    participant T3 as task_3
    participant S as Semaphore(2)
    participant R as Shared resource

    T1->>S: acquire
    S-->>T1: granted
    T2->>S: acquire
    S-->>T2: granted
    T3->>S: acquire
    Note over T3,S: waits because limit reached
    T1->>R: use resource
    T2->>R: use resource
    T1->>S: release
    S-->>T3: granted
    T3->>R: use resource
```



## 9. Offloading blocking work with `asyncio.to_thread(...)`

Key idea:

- The event loop stays responsive because the blocking function runs in a worker thread.
- This helps protect unrelated async work from being stuck behind blocking code.

```mermaid
sequenceDiagram
    participant H as FastAPI handler
    participant L as Event loop
    participant W as Thread worker
    participant B as blocking_func()

    H->>L: await asyncio.to_thread(blocking_func)
    L->>W: submit blocking_func
    W->>B: run blocking code
    Note over H: handler is suspended
    Note over L: loop can serve other requests
    B-->>W: result
    W-->>L: future resolved
    L-->>H: resume handler with result
```



## 10. Cancellation flow

Key idea:

- Cancelling a task raises `CancelledError` inside that coroutine at the next await point.
- Well-behaved coroutines clean up and then re-raise or exit.

```mermaid
sequenceDiagram
    participant M as Main coroutine
    participant T as Task
    participant C as child coroutine

    M->>T: cancel()
    T->>C: inject CancelledError
    Note over C: delivered at next await point
    C->>C: cleanup in finally / except
    C-->>T: cancelled
    T-->>M: task finished as cancelled
```



## Reading Guide

Use these diagrams as a mental model:

- If a coroutine is `await`ing, the loop may run other work.
- If code is CPU-bound and never yields, it blocks progress on that loop thread.
- Tasks are the event loop's units of scheduled coroutine execution.
- Queues and semaphores are coordination tools, not magic performance tools.
- Worker patterns help organize concurrency, but they still depend on where blocking happens.

