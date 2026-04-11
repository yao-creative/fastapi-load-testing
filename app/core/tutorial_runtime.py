import asyncio
import logging
import time

from fastapi import Request


logger = logging.getLogger(__name__)


class TutorialRuntime:
    def __init__(
        self,
        *,
        semaphore_capacity: int = 2,
        queue_maxsize: int = 100,
        queue_worker_count: int = 2,
    ) -> None:
        self.semaphore_capacity = semaphore_capacity
        self.resource_semaphore = asyncio.Semaphore(semaphore_capacity)
        self.job_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=queue_maxsize)
        self.queue_worker_count = queue_worker_count
        self.queue_worker_tasks: list[asyncio.Task] = []
        self.queue_next_job_id = 0
        self.queue_enqueued_total = 0
        self.queue_processed_total = 0
        self.queue_failed_total = 0

    async def semaphore_task(self, hold_seconds: int = 5) -> float:
        started_at = time.perf_counter()
        logger.info(
            "/tutorials/async/bounded/semaphore internal: start hold_seconds=%s",
            hold_seconds,
        )
        await asyncio.sleep(hold_seconds)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "/tutorials/async/bounded/semaphore internal: end duration_ms=%s",
            duration_ms,
        )
        return duration_ms

    async def queue_worker(self, worker_id: int) -> None:
        logger.info("/tutorials/async/queue worker %s: started", worker_id)
        while True:
            job = await self.job_queue.get()
            try:
                work_ms = job["work_ms"]
                job_id = job["job_id"]
                logger.info(
                    "/tutorials/async/queue worker %s: start job_id=%s work_ms=%s",
                    worker_id,
                    job_id,
                    work_ms,
                )
                await asyncio.sleep(work_ms / 1000)
                self.queue_processed_total += 1
                logger.info(
                    "/tutorials/async/queue worker %s: end job_id=%s",
                    worker_id,
                    job_id,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                self.queue_failed_total += 1
                logger.exception(
                    "/tutorials/async/queue worker %s: failed job=%s",
                    worker_id,
                    job,
                )
            finally:
                self.job_queue.task_done()

    async def start_workers(self) -> None:
        self.queue_worker_tasks.clear()
        for worker_id in range(1, self.queue_worker_count + 1):
            self.queue_worker_tasks.append(
                asyncio.create_task(self.queue_worker(worker_id))
            )

    async def stop_workers(self) -> None:
        for task in self.queue_worker_tasks:
            task.cancel()
        if self.queue_worker_tasks:
            await asyncio.gather(*self.queue_worker_tasks, return_exceptions=True)
        self.queue_worker_tasks.clear()

    async def enqueue_jobs(self, n: int, work_ms: int) -> list[int]:
        enqueued_job_ids: list[int] = []
        for _ in range(n):
            self.queue_next_job_id += 1
            job_id = self.queue_next_job_id
            job = {
                "job_id": job_id,
                "work_ms": work_ms,
                "enqueued_at_ms": round(time.time() * 1000),
            }
            await self.job_queue.put(job)
            self.queue_enqueued_total += 1
            enqueued_job_ids.append(job_id)

        return enqueued_job_ids

    def queue_stats(self) -> dict:
        return {
            "status": "ok",
            "queue_size": self.job_queue.qsize(),
            "queue_maxsize": self.job_queue.maxsize,
            "worker_count": len(self.queue_worker_tasks),
            "worker_tasks_running": sum(
                not task.done() for task in self.queue_worker_tasks
            ),
            "enqueued_total": self.queue_enqueued_total,
            "processed_total": self.queue_processed_total,
            "failed_total": self.queue_failed_total,
        }


def get_tutorial_runtime(request: Request) -> TutorialRuntime:
    return request.app.state.tutorial_runtime
