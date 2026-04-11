from fastapi import FastAPI, HTTPException, Query
import asyncio
import time

app = FastAPI(title="fastapi-load-testing", version="0.1.0")

SEMAPHORE_CAPACITY = 2
resource_semaphore = asyncio.Semaphore(SEMAPHORE_CAPACITY)
QUEUE_MAXSIZE = 100
QUEUE_WORKER_COUNT = 2
job_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
queue_worker_tasks: list[asyncio.Task] = []
queue_next_job_id = 0
queue_enqueued_total = 0
queue_processed_total = 0
queue_failed_total = 0


@app.get("/health")
async def health():
    return {"status": "ok"}




# TODO lab outline: keep these as comments until you implement the experiments.
#
# Learning goal 1: show what blocks the event loop inside one worker.
# - GET /sleep/blocking
#   - Use `time.sleep(...)`.
#   - Measure how badly unrelated requests suffer under concurrency.
# - GET /sleep/async
#   - Use `await asyncio.sleep(...)`.
#   - Compare p95/p99 and throughput against `/sleep/blocking`.

@app.get("/sleep/blocking")
async def sleep_blocking(seconds: int = 1):
    print(f"/sleep/blocking: Sleeping for {seconds} seconds")
    time.sleep(seconds)
    return {"status": "ok"}

@app.get("/sleep/async")
async def sleep_async(seconds: int = 1):
    print(f"/sleep/async: Sleeping for {seconds} seconds")
    await asyncio.sleep(seconds)
    return {"status": "ok"}


def run_cpu_work(iterations: int) -> int:
    total = 0
    for i in range(iterations):
        total += (i % 97) * (i % 89)
    return total


#
# Learning goal 2: compare CPU work inline versus offloaded.
# - GET /cpu/inline
#   - Run a CPU-heavy loop directly in the request handler.
#   - Confirm that async syntax does not save CPU-bound work.
@app.get("/cpu/inline")
async def cpu_inline(iterations: int = 25_000_000):
    print(f"/cpu/inline: Running CPU-heavy loop for {iterations} iterations")
    checksum = run_cpu_work(iterations)
    return {"status": "ok", "iterations": iterations, "checksum": checksum}


# - GET /cpu/to-thread
#   - Offload the same blocking CPU function with `asyncio.to_thread(...)`.
#   - Measure whether responsiveness improves for other requests.
@app.get("/cpu/to-thread")
async def cpu_to_thread(iterations: int = 25_000_000):
    print(f"/cpu/to-thread: Running CPU-heavy loop for {iterations} iterations")
    checksum = await asyncio.to_thread(run_cpu_work, iterations)
    return {"status": "ok", "iterations": iterations, "checksum": checksum}


# Learning goal 3: compare sequential and concurrent fan-out.
# - GET /fanout/sequential
#   - Await each subtask one after another.
async def fanout_worker(task_id: int, delay_ms: int = 300):
    started_at = time.perf_counter()
    print(f"/fanout worker {task_id}: start delay_ms={delay_ms}")
    await asyncio.sleep(delay_ms / 1000)
    ended_at = time.perf_counter()
    duration_ms = round((ended_at - started_at) * 1000, 2)
    print(f"/fanout worker {task_id}: end duration_ms={duration_ms}")
    return {"task_id": task_id, "duration_ms": duration_ms}


@app.get("/fanout/sequential")
async def fanout_sequential(num_tasks: int = 15, delay_ms: int = 300):
    request_started_at = time.perf_counter()
    results = []
    for task_id in range(1, num_tasks + 1):
        results.append(await fanout_worker(task_id=task_id, delay_ms=delay_ms))

    total_duration_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    print(
        f"/fanout/sequential: num_tasks={num_tasks} delay_ms={delay_ms} "
        f"total_duration_ms={total_duration_ms}"
    )
    return {
        "status": "ok",
        "num_tasks": num_tasks,
        "delay_ms": delay_ms,
        "total_duration_ms": total_duration_ms,
        "results": results,
    }
# Learning goal 4: practice time budgets, timeouts, and cancellation.
# - GET /timeout/slow
#   - Run one slow awaitable behind `asyncio.timeout(...)`.
#   - Return whether the inner operation finished or timed out.
# - GET /timeout/fanout
#   - Fan out multiple subtasks, then apply a request-level timeout budget.
#   - Observe which subtasks are cancelled when the budget expires.
# - Add logs in `try/except/finally` so you can see:
#   - when cancellation is raised,
#   - whether cleanup still runs,
#   - and whether any work leaks after the request is over.
#
# Concept to internalize:
# - Timeouts are not just latency controls; they are cancellation boundaries.
# - Good async code must clean up correctly when cancelled midway through work.
#


async def timeout_worker(task_id: int, delay_ms: int = 300):
    started_at = time.perf_counter()
    print(f"/timeout worker {task_id}: start delay_ms={delay_ms}")
    try:
        await asyncio.sleep(delay_ms / 1000)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        print(f"/timeout worker {task_id}: end duration_ms={duration_ms}")
        return {"task_id": task_id, "duration_ms": duration_ms, "status": "completed"}
    except asyncio.CancelledError:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        print(f"/timeout worker {task_id}: cancelled duration_ms={duration_ms}")
        raise
    finally:
        cleanup_ms = round((time.perf_counter() - started_at) * 1000, 2)
        print(f"/timeout worker {task_id}: cleanup cleanup_ms={cleanup_ms}")


@app.get("/timeout/slow")
async def timeout_slow(
    delay_ms: int = Query(default=1_000, ge=1, le=60_000),
    timeout_ms: int = Query(default=500, ge=1, le=60_000),
):
    request_started_at = time.perf_counter()
    try:
        async with asyncio.timeout(timeout_ms / 1000):
            result = await timeout_worker(task_id=1, delay_ms=delay_ms)
        total_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
        print(
            f"/timeout/slow: completed delay_ms={delay_ms} "
            f"timeout_ms={timeout_ms} total_ms={total_ms}"
        )
        return {
            "status": "completed",
            "delay_ms": delay_ms,
            "timeout_ms": timeout_ms,
            "completed_tasks": 1,
            "cancelled_tasks": 0,
            "total_ms": total_ms,
            "result": result,
        }
    except TimeoutError:
        total_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
        print(
            f"/timeout/slow: timed_out delay_ms={delay_ms} "
            f"timeout_ms={timeout_ms} total_ms={total_ms}"
        )
        return {
            "status": "timed_out",
            "delay_ms": delay_ms,
            "timeout_ms": timeout_ms,
            "completed_tasks": 0,
            "cancelled_tasks": 1,
            "total_ms": total_ms,
        }


@app.get("/timeout/fanout")
async def timeout_fanout(
    num_tasks: int = Query(default=15, ge=1, le=500),
    delay_ms: int = Query(default=300, ge=1, le=60_000),
    timeout_ms: int = Query(default=500, ge=1, le=60_000),
):
    request_started_at = time.perf_counter()
    tasks = [
        asyncio.create_task(timeout_worker(task_id=task_id, delay_ms=delay_ms))
        for task_id in range(1, num_tasks + 1)
    ]

    try:
        async with asyncio.timeout(timeout_ms / 1000):
            results = await asyncio.gather(*tasks)
   
        completed_tasks = sum(1 for task in tasks if task.done() and not task.cancelled())
        total_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
        print(
            f"/timeout/fanout: completed num_tasks={num_tasks} delay_ms={delay_ms} "
            f"timeout_ms={timeout_ms} completed_tasks={completed_tasks} total_ms={total_ms}"
        )
        return {
            "status": "completed",
            "num_tasks": num_tasks,
            "delay_ms": delay_ms,
            "timeout_ms": timeout_ms,
            "completed_tasks": completed_tasks,
            "cancelled_tasks": 0,
            "total_ms": total_ms,
            "results": results,
        }
    except TimeoutError:
        await asyncio.gather(*tasks, return_exceptions=True)
        completed_tasks = sum(1 for task in tasks if task.done() and not task.cancelled())
        cancelled_tasks = sum(1 for task in tasks if task.cancelled())
        total_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
        print(
            f"/timeout/fanout: timed_out num_tasks={num_tasks} delay_ms={delay_ms} "
            f"timeout_ms={timeout_ms} completed_tasks={completed_tasks} "
            f"cancelled_tasks={cancelled_tasks} total_ms={total_ms}"
        )
        return {
            "status": "timed_out",
            "num_tasks": num_tasks,
            "delay_ms": delay_ms,
            "timeout_ms": timeout_ms,
            "completed_tasks": completed_tasks,
            "cancelled_tasks": cancelled_tasks,
            "total_ms": total_ms,
        }



# - GET /fanout/gather
#   - Run the same subtasks with `asyncio.gather(...)`.
# - Add timestamps so the scheduling difference is visible in logs.
#
@app.get("/fanout/gather")
async def fanout_gather(num_tasks: int = 15, delay_ms: int = 300):
    request_started_at = time.perf_counter()
    results = await asyncio.gather(
        *(fanout_worker(task_id=task_id, delay_ms=delay_ms) for task_id in range(1, num_tasks + 1))
    )

    total_duration_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    print(
        f"/fanout/gather: num_tasks={num_tasks} delay_ms={delay_ms} "
        f"total_duration_ms={total_duration_ms}"
    )
    return {
        "status": "ok",
        "num_tasks": num_tasks,
        "delay_ms": delay_ms,
        "total_duration_ms": total_duration_ms,
        "results": results,
    }


# Learning goal 5: simulate bounded shared resources.
# - Add an `asyncio.Semaphore` around a section that represents a DB pool or
#   external service bottleneck.
# - Test what happens when concurrent requests exceed the artificial capacity.
#
# Deployment experiment notes:
# - Re-run the same endpoints with one worker and then with multiple workers.
# - Check which failures come from bad app behavior versus worker-count limits.

async def semaphore_task(hold_seconds: int = 5):
    started_at = time.perf_counter()
    print(f"/bounded/semaphore internal: start hold_seconds={hold_seconds}")
    await asyncio.sleep(hold_seconds)
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    print(f"/bounded/semaphore internal: end duration_ms={duration_ms}")
    return duration_ms


@app.get("/bounded/semaphore")
async def bounded_semaphore(hold_seconds: int = 5, outside_seconds: int = 0):
    request_started_at = time.perf_counter()

    if outside_seconds > 0:
        await asyncio.sleep(outside_seconds)

    wait_started_at = time.perf_counter()
    async with resource_semaphore:
        wait_ms = round((time.perf_counter() - wait_started_at) * 1000, 2)
        in_cs_ms = await semaphore_task(hold_seconds=hold_seconds)

    total_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    print(
        f"/bounded/semaphore: capacity={SEMAPHORE_CAPACITY} "
        f"hold_seconds={hold_seconds} outside_seconds={outside_seconds} "
        f"wait_ms={wait_ms} in_cs_ms={in_cs_ms} total_ms={total_ms}"
    ) 
    return {
        "status": "ok",
        "capacity": SEMAPHORE_CAPACITY,
        "hold_seconds": hold_seconds,
        "outside_seconds": outside_seconds,
        "wait_ms": wait_ms,
        "in_cs_ms": in_cs_ms,
        "total_ms": total_ms,
    }

# Learning Goal 6: Producer- Consumer Queues
# - POST /queue/enqueue
#   - Enqueue N jobs into an in-memory `asyncio.Queue` and return immediately.
#   - Observe that background workers can keep consuming after the request ends.
# - POST /queue/drain
#   - Enqueue N jobs, then `await queue.join()` before returning.
#   - Compare request latency versus `/queue/enqueue`.
# - GET /queue/stats
#   - Return current queue size and worker counters for debugging.
#
# Important teaching point:
# - `asyncio.Queue` coordinates producers and consumers inside one process and
#   can provide natural backpressure when `maxsize` is set.
# - `queue.join()` is a completion barrier for queued work; it is not what
#   starts or stops worker tasks.
#
# Future implementation notes:
# - Create one shared queue per process and start a fixed number of worker tasks
#   at app startup.
# - Under multiple Uvicorn workers, each process has its own queue and workers.


#   The important separation is:

#   - asyncio event loop: the scheduler that runs
#     coroutines/tasks.
#   - queue_worker() loop: your application’s
#     consumer logic that repeatedly does get ->
#     process -> task_done.
#   - /queue/enqueue: submit work and return.
#   - /queue/drain: submit work and then wait for
#     consumers to finish it with queue.join().

#   So:

#   - Without consumers, /queue/enqueue can still put
#     items into the queue, but nothing will ever
#     process them.
#   - Without consumers, /queue/drain will hang
#     forever, because join() only resumes after
#     workers call task_done().
#   - The queue does not “auto-consume” just because
#     you are using asyncio.

async def queue_worker(worker_id: int) -> None:
    global queue_failed_total
    global queue_processed_total

    print(f"/queue worker {worker_id}: started")
    while True:
        job = await job_queue.get()
        try:
            work_ms = job["work_ms"]
            job_id = job["job_id"]
            print(f"/queue worker {worker_id}: start job_id={job_id} work_ms={work_ms}")
            await asyncio.sleep(work_ms / 1000)
            queue_processed_total += 1
            print(f"/queue worker {worker_id}: end job_id={job_id}")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            queue_failed_total += 1
            print(f"/queue worker {worker_id}: failed job={job} exc={exc!r}")
        finally:
            job_queue.task_done()


@app.on_event("startup")
async def startup_queue_workers() -> None:
    queue_worker_tasks.clear()
    for worker_id in range(1, QUEUE_WORKER_COUNT + 1):
        queue_worker_tasks.append(asyncio.create_task(queue_worker(worker_id)))


@app.on_event("shutdown")
async def shutdown_queue_workers() -> None:
    for task in queue_worker_tasks:
        task.cancel()
    if queue_worker_tasks:
        await asyncio.gather(*queue_worker_tasks, return_exceptions=True)
    queue_worker_tasks.clear()


#   What is safe here:

#   - queue_next_job_id:
#       - safe enough in one event loop because there
#         is no await between reading/updating it
#   - queue_enqueued_total += 1:
#       - also safe enough for the same reason
#   - await job_queue.put(job):
#       - safe for coroutine coordination;
#         asyncio.Queue is designed for this

#  So the right label is:

#   - coroutine-safe enough within one process
#   - not thread-safe in the general sense
#   - not cross-process safe

async def enqueue_jobs(n: int, work_ms: int) -> list[int]:
    global queue_enqueued_total
    global queue_next_job_id

    enqueued_job_ids: list[int] = []
    for _ in range(n):
        queue_next_job_id += 1
        job_id = queue_next_job_id
        job = {
            "job_id": job_id,
            "work_ms": work_ms,
            "enqueued_at_ms": round(time.time() * 1000),
        }
        await job_queue.put(job)
        queue_enqueued_total += 1
        enqueued_job_ids.append(job_id)

    return enqueued_job_ids

# enqueue = “submit work”
@app.post("/queue/enqueue")
async def queue_enqueue(
    n: int = Query(default=10, ge=1, le=500),
    work_ms: int = Query(default=250, ge=1, le=60_000),
):
    request_started_at = time.perf_counter()
    job_ids = await enqueue_jobs(n=n, work_ms=work_ms)
    request_duration_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    print(
        f"/queue/enqueue: n={n} work_ms={work_ms} "
        f"queue_size={job_queue.qsize()} request_duration_ms={request_duration_ms}"
    )
    return {
        "status": "accepted",
        "mode": "enqueue_only",
        "enqueued": len(job_ids),
        "job_ids": job_ids,
        "work_ms": work_ms,
        "queue_size": job_queue.qsize(),
        "worker_count": len(queue_worker_tasks),
        "request_duration_ms": request_duration_ms,
    }

# drain = "submit work and wait until all queued work is finished"
@app.post("/queue/drain")
async def queue_drain(
    n: int = Query(default=10, ge=1, le=500),
    work_ms: int = Query(default=250, ge=1, le=60_000),
):
    request_started_at = time.perf_counter()
    job_ids = await enqueue_jobs(n=n, work_ms=work_ms)
    enqueue_duration_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    await job_queue.join()
    total_duration_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    print(
        f"/queue/drain: n={n} work_ms={work_ms} "
        f"enqueue_duration_ms={enqueue_duration_ms} total_duration_ms={total_duration_ms}"
    )
    return {
        "status": "ok",
        "mode": "enqueue_and_wait_for_drain",
        "enqueued": len(job_ids),
        "job_ids": job_ids,
        "work_ms": work_ms,
        "queue_size": job_queue.qsize(),
        "worker_count": len(queue_worker_tasks),
        "enqueue_duration_ms": enqueue_duration_ms,
        "total_duration_ms": total_duration_ms,
    }


@app.get("/queue/stats")
async def queue_stats():
    return {
        "status": "ok",
        "queue_size": job_queue.qsize(),
        "queue_maxsize": job_queue.maxsize,
        "worker_count": len(queue_worker_tasks),
        "worker_tasks_running": sum(not task.done() for task in queue_worker_tasks),
        "enqueued_total": queue_enqueued_total,
        "processed_total": queue_processed_total,
        "failed_total": queue_failed_total,
    }

# Learning Goal 6.2 Simulating Producer and consumer on a qQueue
async def _simulate_producer(q: asyncio.Queue, seconds: float, num_items: int) -> None:
    for i in range(num_items):
        await q.put(i)
        print(f"Produced item {i}")
        await asyncio.sleep(seconds)
    await q.put(None)


async def _simulate_consumer(q: asyncio.Queue, seconds: float) -> None:
    while True:
        item = await q.get()
        try:
            if item is None:
                break
            print(f"Consumed {item}")
            await asyncio.sleep(seconds)
        finally:
            q.task_done()


@app.get("/simulate/queue")
async def simulate_queue(seconds: int = 2, num_items: int = 5):
    q: asyncio.Queue = asyncio.Queue()
    consumer_task = asyncio.create_task(_simulate_consumer(q, float(seconds)))
    await _simulate_producer(q, float(seconds), num_items)
    await q.join()
    await consumer_task
    return {"status": "ok", "num_items": num_items}



# Learning goal 7: compare failure propagation in `asyncio.gather(...)`
# versus structured concurrency with `asyncio.TaskGroup`.
# - GET /fanout/gather-fail
#   - Start multiple subtasks where one fails after a delay.
#   - Observe whether sibling subtasks keep running or how exceptions surface.
# - GET /fanout/taskgroup-fail
#   - Run the same workload under `asyncio.TaskGroup`.
#   - Observe how sibling tasks are cancelled and how the failure is reported.
# - Return enough metadata to answer:
#   - which task failed first,
#   - which tasks completed,
#   - which tasks were cancelled,
#   - and how long the request ran before failing.
#
# Concept to internalize:
# - Concurrency is not just about speed; failure behavior is part of the API contract.
# - `gather(...)` and `TaskGroup` can produce very different cleanup behavior.

class FanoutWorkerError(Exception):
    def __init__(self, task_id: int):
        super().__init__(f"Task {task_id} failed intentionally")
        self.task_id = task_id


async def worker_with_failure(
    *,
    label: str,
    task_id: int,
    fail_task: int,
    delay_ms: int,
):
    started_at = time.perf_counter()
    print(f"{label} worker {task_id}: start delay_ms={delay_ms}")
    try:
        if task_id == fail_task:
            # Fail earlier than sibling tasks so TaskGroup cancellation is visible.
            await asyncio.sleep((delay_ms / 2) / 1000)
            print(f"{label} worker {task_id}: FAILING as requested")
            raise FanoutWorkerError(task_id)
        await asyncio.sleep(delay_ms / 1000)

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        print(f"{label} worker {task_id}: done duration_ms={duration_ms}")
        return {"task_id": task_id, "status": "completed", "duration_ms": duration_ms}
    except asyncio.CancelledError:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        print(f"{label} worker {task_id}: cancelled duration_ms={duration_ms}")
        raise
    finally:
        cleanup_ms = round((time.perf_counter() - started_at) * 1000, 2)
        print(f"{label} worker {task_id}: cleanup cleanup_ms={cleanup_ms}")


def _iter_leaf_exceptions(exc: BaseException):
    if isinstance(exc, BaseExceptionGroup):
        for inner in exc.exceptions:
            yield from _iter_leaf_exceptions(inner)
    else:
        yield exc


def _collect_task_outcomes(tasks: dict[int, asyncio.Task]) -> tuple[list[int], list[int], list[dict], list[dict]]:
    completed_tasks: list[int] = []
    cancelled_tasks: list[int] = []
    failed_tasks: list[dict] = []
    terminal_states: list[dict] = []

    for task_id, task in tasks.items():
        if task.cancelled():
            cancelled_tasks.append(task_id)
            terminal_states.append({"task_id": task_id, "status": "cancelled"})
            continue

        if not task.done():
            terminal_states.append({"task_id": task_id, "status": "pending"})
            continue

        exc = task.exception()
        if exc is not None:
            failed_tasks.append({"task_id": task_id, "exception": str(exc)})
            terminal_states.append(
                {"task_id": task_id, "status": "failed", "exception": str(exc)}
            )
            continue

        result = task.result()
        completed_tasks.append(task_id)
        terminal_states.append(
            {
                "task_id": task_id,
                "status": "completed",
                "duration_ms": result["duration_ms"],
            }
        )

    return completed_tasks, cancelled_tasks, failed_tasks, terminal_states


def _validate_fail_task(num_tasks: int, fail_task: int) -> None:
    if fail_task > num_tasks:
        raise HTTPException(
            status_code=422,
            detail=f"fail_task must be between 1 and num_tasks ({num_tasks})",
        )


@app.get("/fanout/gather-fail")
async def gather_fail_endpoint(
    num_tasks: int = Query(default=7, ge=1, le=100),
    fail_task: int = Query(default=3, ge=1, le=100),
    delay_ms: int = Query(default=200, ge=1, le=60_000),
    timeout_ms: int = Query(default=1_500, ge=1, le=60_000),
):
    request_started_at = time.perf_counter()
    _validate_fail_task(num_tasks=num_tasks, fail_task=fail_task)
    tasks = {
        task_id: asyncio.create_task(
            worker_with_failure(
                label="/fanout/gather-fail",
                task_id=task_id,
                fail_task=fail_task,
                delay_ms=delay_ms,
            )
        )
        for task_id in range(1, num_tasks + 1)
    }

    status = "completed"
    first_exception = None

    try:
        async with asyncio.timeout(timeout_ms / 1000):
            await asyncio.gather(*tasks.values())
    except TimeoutError:
        status = "timed_out"
        first_exception = "request timed out"
        await asyncio.gather(*tasks.values(), return_exceptions=True)
    except Exception as exc:
        status = "failed"
        first_exception = str(exc)
        # `gather(...)` surfaces the first failure immediately. We then wait for
        # remaining tasks to settle so the response can show sibling behavior.
        await asyncio.gather(*tasks.values(), return_exceptions=True)

    completed_tasks, cancelled_tasks, failed_tasks, terminal_states = _collect_task_outcomes(tasks)
    total_ms = round((time.perf_counter() - request_started_at) * 1000, 2)

    return {
        "status": status,
        "num_tasks": num_tasks,
        "fail_task": fail_task,
        "delay_ms": delay_ms,
        "timeout_ms": timeout_ms,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "cancelled_tasks": cancelled_tasks,
        "first_exception": first_exception,
        "total_ms": total_ms,
        "task_terminal_states": terminal_states,
    }


@app.get("/fanout/taskgroup-fail")
async def taskgroup_fail_endpoint(
    num_tasks: int = Query(default=7, ge=1, le=100),
    fail_task: int = Query(default=3, ge=1, le=100),
    delay_ms: int = Query(default=200, ge=1, le=60_000),
    timeout_ms: int = Query(default=1_500, ge=1, le=60_000),
):
    request_started_at = time.perf_counter()
    _validate_fail_task(num_tasks=num_tasks, fail_task=fail_task)
    tasks: dict[int, asyncio.Task] = {}
    status = "completed"
    first_exception = None
    failed_task_id = None

    try:
        async with asyncio.timeout(timeout_ms / 1000):
            async with asyncio.TaskGroup() as task_group:
                for task_id in range(1, num_tasks + 1):
                    tasks[task_id] = task_group.create_task(
                        worker_with_failure(
                            label="/fanout/taskgroup-fail",
                            task_id=task_id,
                            fail_task=fail_task,
                            delay_ms=delay_ms,
                        )
                    )
    except TimeoutError:
        status = "timed_out"
        first_exception = "request timed out"
    except Exception as exc:
        status = "failed"
        leaf_exceptions = list(_iter_leaf_exceptions(exc))
        first_exception = str(leaf_exceptions[0]) if leaf_exceptions else str(exc)
        for inner in leaf_exceptions:
            if isinstance(inner, FanoutWorkerError):
                failed_task_id = inner.task_id
                break

    completed_tasks, cancelled_tasks, failed_tasks, terminal_states = _collect_task_outcomes(tasks)
    total_ms = round((time.perf_counter() - request_started_at) * 1000, 2)

    return {
        "status": status,
        "num_tasks": num_tasks,
        "fail_task": fail_task,
        "delay_ms": delay_ms,
        "timeout_ms": timeout_ms,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "cancelled_tasks": cancelled_tasks,
        "first_exception": first_exception,
        "failed_task_id": failed_task_id,
        "total_ms": total_ms,
        "task_terminal_states": terminal_states,
    }



# Learning goal 8: practice shared mutable state, race conditions, and locks.
# - POST /state/increment/unsafe
#   - Read a shared counter, yield, then write back without protection.
#   - Under concurrent requests, show lost updates.
# - POST /state/increment/locked
#   - Protect the same critical section with `asyncio.Lock`.
#   - Compare correctness and latency against the unsafe version.
# - GET /state/value
#   - Return the current in-memory counter for debugging.
#
# Important teaching point:
# - Even on one event loop thread, async code can still race if it yields between
#   read-modify-write steps.
# - `asyncio.Lock` protects coroutine interleavings inside one process; it does not
#   synchronize across multiple Uvicorn workers.
# Pass for now have done before and i get the generic thing os shared states such as counter and conditions.
