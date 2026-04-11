import asyncio
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.tutorial_runtime import TutorialRuntime, get_tutorial_runtime


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutorials/async", tags=["tutorials-async"])


@router.get("/sleep/blocking")
async def sleep_blocking(seconds: int = 1):
    logger.info("/tutorials/async/sleep/blocking: sleeping for %s seconds", seconds)
    time.sleep(seconds)
    return {"status": "ok"}


@router.get("/sleep/async")
async def sleep_async(seconds: int = 1):
    logger.info("/tutorials/async/sleep/async: sleeping for %s seconds", seconds)
    await asyncio.sleep(seconds)
    return {"status": "ok"}


def run_cpu_work(iterations: int) -> int:
    total = 0
    for i in range(iterations):
        total += (i % 97) * (i % 89)
    return total


@router.get("/cpu/inline")
async def cpu_inline(iterations: int = 25_000_000):
    logger.info(
        "/tutorials/async/cpu/inline: running CPU-heavy loop for %s iterations",
        iterations,
    )
    checksum = run_cpu_work(iterations)
    return {"status": "ok", "iterations": iterations, "checksum": checksum}


@router.get("/cpu/to-thread")
async def cpu_to_thread(iterations: int = 25_000_000):
    logger.info(
        "/tutorials/async/cpu/to-thread: running CPU-heavy loop for %s iterations",
        iterations,
    )
    checksum = await asyncio.to_thread(run_cpu_work, iterations)
    return {"status": "ok", "iterations": iterations, "checksum": checksum}


async def fanout_worker(task_id: int, delay_ms: int = 300):
    started_at = time.perf_counter()
    logger.info("/tutorials/async/fanout worker %s: start delay_ms=%s", task_id, delay_ms)
    await asyncio.sleep(delay_ms / 1000)
    ended_at = time.perf_counter()
    duration_ms = round((ended_at - started_at) * 1000, 2)
    logger.info(
        "/tutorials/async/fanout worker %s: end duration_ms=%s",
        task_id,
        duration_ms,
    )
    return {"task_id": task_id, "duration_ms": duration_ms}


@router.get("/fanout/sequential")
async def fanout_sequential(num_tasks: int = 15, delay_ms: int = 300):
    request_started_at = time.perf_counter()
    results = []
    for task_id in range(1, num_tasks + 1):
        results.append(await fanout_worker(task_id=task_id, delay_ms=delay_ms))

    total_duration_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    logger.info(
        "/tutorials/async/fanout/sequential: num_tasks=%s delay_ms=%s total_duration_ms=%s",
        num_tasks,
        delay_ms,
        total_duration_ms,
    )
    return {
        "status": "ok",
        "num_tasks": num_tasks,
        "delay_ms": delay_ms,
        "total_duration_ms": total_duration_ms,
        "results": results,
    }


async def timeout_worker(task_id: int, delay_ms: int = 300):
    started_at = time.perf_counter()
    logger.info("/tutorials/async/timeout worker %s: start delay_ms=%s", task_id, delay_ms)
    try:
        await asyncio.sleep(delay_ms / 1000)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "/tutorials/async/timeout worker %s: end duration_ms=%s",
            task_id,
            duration_ms,
        )
        return {"task_id": task_id, "duration_ms": duration_ms, "status": "completed"}
    except asyncio.CancelledError:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "/tutorials/async/timeout worker %s: cancelled duration_ms=%s",
            task_id,
            duration_ms,
        )
        raise
    finally:
        cleanup_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "/tutorials/async/timeout worker %s: cleanup cleanup_ms=%s",
            task_id,
            cleanup_ms,
        )


@router.get("/timeout/slow")
async def timeout_slow(
    delay_ms: int = Query(default=1_000, ge=1, le=60_000),
    timeout_ms: int = Query(default=500, ge=1, le=60_000),
):
    request_started_at = time.perf_counter()
    try:
        async with asyncio.timeout(timeout_ms / 1000):
            result = await timeout_worker(task_id=1, delay_ms=delay_ms)
        total_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
        logger.info(
            "/tutorials/async/timeout/slow: completed delay_ms=%s timeout_ms=%s total_ms=%s",
            delay_ms,
            timeout_ms,
            total_ms,
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
        logger.info(
            "/tutorials/async/timeout/slow: timed_out delay_ms=%s timeout_ms=%s total_ms=%s",
            delay_ms,
            timeout_ms,
            total_ms,
        )
        return {
            "status": "timed_out",
            "delay_ms": delay_ms,
            "timeout_ms": timeout_ms,
            "completed_tasks": 0,
            "cancelled_tasks": 1,
            "total_ms": total_ms,
        }


@router.get("/timeout/fanout")
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
        logger.info(
            "/tutorials/async/timeout/fanout: completed num_tasks=%s delay_ms=%s timeout_ms=%s completed_tasks=%s total_ms=%s",
            num_tasks,
            delay_ms,
            timeout_ms,
            completed_tasks,
            total_ms,
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
        logger.info(
            "/tutorials/async/timeout/fanout: timed_out num_tasks=%s delay_ms=%s timeout_ms=%s completed_tasks=%s cancelled_tasks=%s total_ms=%s",
            num_tasks,
            delay_ms,
            timeout_ms,
            completed_tasks,
            cancelled_tasks,
            total_ms,
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


@router.get("/fanout/gather")
async def fanout_gather(num_tasks: int = 15, delay_ms: int = 300):
    request_started_at = time.perf_counter()
    results = await asyncio.gather(
        *(fanout_worker(task_id=task_id, delay_ms=delay_ms) for task_id in range(1, num_tasks + 1))
    )

    total_duration_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    logger.info(
        "/tutorials/async/fanout/gather: num_tasks=%s delay_ms=%s total_duration_ms=%s",
        num_tasks,
        delay_ms,
        total_duration_ms,
    )
    return {
        "status": "ok",
        "num_tasks": num_tasks,
        "delay_ms": delay_ms,
        "total_duration_ms": total_duration_ms,
        "results": results,
    }


@router.get("/bounded/semaphore")
async def bounded_semaphore(
    hold_seconds: int = 5,
    outside_seconds: int = 0,
    runtime: TutorialRuntime = Depends(get_tutorial_runtime),
):
    request_started_at = time.perf_counter()

    if outside_seconds > 0:
        await asyncio.sleep(outside_seconds)

    wait_started_at = time.perf_counter()
    async with runtime.resource_semaphore:
        wait_ms = round((time.perf_counter() - wait_started_at) * 1000, 2)
        in_cs_ms = await runtime.semaphore_task(hold_seconds=hold_seconds)

    total_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    logger.info(
        "/tutorials/async/bounded/semaphore: capacity=%s hold_seconds=%s outside_seconds=%s wait_ms=%s in_cs_ms=%s total_ms=%s",
        runtime.semaphore_capacity,
        hold_seconds,
        outside_seconds,
        wait_ms,
        in_cs_ms,
        total_ms,
    )
    return {
        "status": "ok",
        "capacity": runtime.semaphore_capacity,
        "hold_seconds": hold_seconds,
        "outside_seconds": outside_seconds,
        "wait_ms": wait_ms,
        "in_cs_ms": in_cs_ms,
        "total_ms": total_ms,
    }


@router.post("/queue/enqueue")
async def queue_enqueue(
    n: int = Query(default=10, ge=1, le=500),
    work_ms: int = Query(default=250, ge=1, le=60_000),
    runtime: TutorialRuntime = Depends(get_tutorial_runtime),
):
    request_started_at = time.perf_counter()
    job_ids = await runtime.enqueue_jobs(n=n, work_ms=work_ms)
    request_duration_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    logger.info(
        "/tutorials/async/queue/enqueue: n=%s work_ms=%s queue_size=%s request_duration_ms=%s",
        n,
        work_ms,
        runtime.job_queue.qsize(),
        request_duration_ms,
    )
    return {
        "status": "accepted",
        "mode": "enqueue_only",
        "enqueued": len(job_ids),
        "job_ids": job_ids,
        "work_ms": work_ms,
        "queue_size": runtime.job_queue.qsize(),
        "worker_count": len(runtime.queue_worker_tasks),
        "request_duration_ms": request_duration_ms,
    }


@router.post("/queue/drain")
async def queue_drain(
    n: int = Query(default=10, ge=1, le=500),
    work_ms: int = Query(default=250, ge=1, le=60_000),
    runtime: TutorialRuntime = Depends(get_tutorial_runtime),
):
    request_started_at = time.perf_counter()
    job_ids = await runtime.enqueue_jobs(n=n, work_ms=work_ms)
    enqueue_duration_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    await runtime.job_queue.join()
    total_duration_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    logger.info(
        "/tutorials/async/queue/drain: n=%s work_ms=%s enqueue_duration_ms=%s total_duration_ms=%s",
        n,
        work_ms,
        enqueue_duration_ms,
        total_duration_ms,
    )
    return {
        "status": "ok",
        "mode": "enqueue_and_wait_for_drain",
        "enqueued": len(job_ids),
        "job_ids": job_ids,
        "work_ms": work_ms,
        "queue_size": runtime.job_queue.qsize(),
        "worker_count": len(runtime.queue_worker_tasks),
        "enqueue_duration_ms": enqueue_duration_ms,
        "total_duration_ms": total_duration_ms,
    }


@router.get("/queue/stats")
async def queue_stats(runtime: TutorialRuntime = Depends(get_tutorial_runtime)):
    return runtime.queue_stats()


async def _simulate_producer(q: asyncio.Queue, seconds: float, num_items: int) -> None:
    for i in range(num_items):
        await q.put(i)
        logger.info("Produced item %s", i)
        await asyncio.sleep(seconds)
    await q.put(None)


async def _simulate_consumer(q: asyncio.Queue, seconds: float) -> None:
    while True:
        item = await q.get()
        try:
            if item is None:
                break
            logger.info("Consumed %s", item)
            await asyncio.sleep(seconds)
        finally:
            q.task_done()


@router.get("/simulate/queue")
async def simulate_queue(seconds: int = 2, num_items: int = 5):
    q: asyncio.Queue = asyncio.Queue()
    consumer_task = asyncio.create_task(_simulate_consumer(q, float(seconds)))
    await _simulate_producer(q, float(seconds), num_items)
    await q.join()
    await consumer_task
    return {"status": "ok", "num_items": num_items}


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
    logger.info("%s worker %s: start delay_ms=%s", label, task_id, delay_ms)
    try:
        if task_id == fail_task:
            await asyncio.sleep((delay_ms / 2) / 1000)
            logger.info("%s worker %s: FAILING as requested", label, task_id)
            raise FanoutWorkerError(task_id)
        await asyncio.sleep(delay_ms / 1000)

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info("%s worker %s: done duration_ms=%s", label, task_id, duration_ms)
        return {"task_id": task_id, "status": "completed", "duration_ms": duration_ms}
    except asyncio.CancelledError:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info("%s worker %s: cancelled duration_ms=%s", label, task_id, duration_ms)
        raise
    finally:
        cleanup_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info("%s worker %s: cleanup cleanup_ms=%s", label, task_id, cleanup_ms)


def _iter_leaf_exceptions(exc: BaseException):
    if isinstance(exc, BaseExceptionGroup):
        for inner in exc.exceptions:
            yield from _iter_leaf_exceptions(inner)
    else:
        yield exc


def _collect_task_outcomes(
    tasks: dict[int, asyncio.Task],
) -> tuple[list[int], list[int], list[dict], list[dict]]:
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


@router.get("/fanout/gather-fail")
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
                label="/tutorials/async/fanout/gather-fail",
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


@router.get("/fanout/taskgroup-fail")
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
                            label="/tutorials/async/fanout/taskgroup-fail",
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
