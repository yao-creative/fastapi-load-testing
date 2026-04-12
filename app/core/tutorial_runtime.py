import asyncio
import logging
import time
from collections.abc import Awaitable

from fastapi import HTTPException, Request


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

        # This is a teaching runtime, not a real Celery worker pool. The goal is to
        # make broker queues, workers, task state, retries, and fan-in visible from
        # the FastAPI tutorial routes without requiring a separate Redis/Celery stack.
        self.celery_broker_queues: dict[str, asyncio.Queue[str]] = {
            "light": asyncio.Queue(),
            "heavy": asyncio.Queue(),
        }
        self.celery_worker_plan: tuple[tuple[str, str], ...] = (
            ("light", "light-1"),
            ("light", "light-2"),
            ("heavy", "heavy-1"),
        )
        self.celery_worker_tasks: list[asyncio.Task] = []
        self.celery_background_tasks: set[asyncio.Task] = set()
        self.celery_next_task_id = 0
        self.celery_next_group_id = 0
        self.celery_tasks: dict[str, dict] = {}
        self.celery_groups: dict[str, dict] = {}
        self.celery_submitted_total = 0
        self.celery_processed_total = 0
        self.celery_failed_total = 0
        self.celery_retry_total = 0
        self.celery_deduped_total = 0

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

    async def celery_worker(self, queue_name: str, worker_id: str) -> None:
        logger.info(
            "/tutorials/celery-redis/worker %s: started queue=%s",
            worker_id,
            queue_name,
        )
        broker_queue = self.celery_broker_queues[queue_name]
        while True:
            task_id = await broker_queue.get()
            try:
                await self._run_celery_task(task_id=task_id, queue_name=queue_name, worker_id=worker_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "/tutorials/celery-redis/worker %s: failed task_id=%s",
                    worker_id,
                    task_id,
                )
            finally:
                broker_queue.task_done()

    async def _run_celery_task(self, *, task_id: str, queue_name: str, worker_id: str) -> None:
        task_record = self.celery_tasks[task_id]
        task_record["attempts"] += 1
        attempt = task_record["attempts"]
        self._set_task_state(
            task_record,
            "STARTED",
            stage="started",
            worker_id=worker_id,
            queue=queue_name,
        )
        logger.info(
            "/tutorials/celery-redis/task %s: start queue=%s worker=%s attempt=%s kind=%s",
            task_id,
            queue_name,
            worker_id,
            attempt,
            task_record["kind"],
        )

        if task_record.get("idempotency_key") and task_record["idempotency_key"] in self._successful_idempotency_keys():
            self.celery_deduped_total += 1
            self._set_task_state(
                task_record,
                "SUCCESS",
                stage="deduped",
                deduped=True,
            )
            task_record["result"] = {
                "status": "deduped",
                "task_id": task_id,
                "idempotency_key": task_record["idempotency_key"],
            }
            self.celery_processed_total += 1
            logger.info("/tutorials/celery-redis/task %s: deduped", task_id)
            return

        if task_record["kind"] == "fanout_callback":
            await self._run_callback_task(task_record=task_record, worker_id=worker_id)
            return

        stage_names = task_record["stage_names"]
        stage_sleep_ms = max(1, task_record["work_ms"] // max(1, len(stage_names)))
        for stage_name in stage_names:
            self._set_task_state(task_record, "PROGRESS", stage=stage_name, worker_id=worker_id)
            await asyncio.sleep(stage_sleep_ms / 1000)

        if attempt <= task_record["fail_until_attempt"]:
            backoff_ms = min(200 * attempt, 1_000)
            self.celery_retry_total += 1
            self._set_task_state(
                task_record,
                "RETRY",
                stage="retry_scheduled",
                retry_in_ms=backoff_ms,
                worker_id=worker_id,
            )
            logger.info(
                "/tutorials/celery-redis/task %s: retry scheduled attempt=%s backoff_ms=%s",
                task_id,
                attempt,
                backoff_ms,
            )
            self._spawn_background_task(self._requeue_celery_task(task_id=task_id, queue_name=queue_name, delay_ms=backoff_ms))
            return

        task_record["result"] = {
            "status": "ok",
            "task_id": task_id,
            "attempts": attempt,
            "queue": queue_name,
            "worker_id": worker_id,
            "work_ms": task_record["work_ms"],
            "kind": task_record["kind"],
        }
        self._set_task_state(task_record, "SUCCESS", stage="done", worker_id=worker_id)
        self.celery_processed_total += 1
        if task_record.get("idempotency_key"):
            task_record["idempotency_completed"] = True
        logger.info(
            "/tutorials/celery-redis/task %s: success queue=%s worker=%s attempt=%s",
            task_id,
            queue_name,
            worker_id,
            attempt,
        )

        if task_record.get("group_id"):
            await self._handle_group_child_success(task_record)

    async def _run_callback_task(self, *, task_record: dict, worker_id: str) -> None:
        group_id = task_record["group_id"]
        group_record = self.celery_groups[group_id]
        await asyncio.sleep(task_record["work_ms"] / 1000)
        child_results = [
            self.celery_tasks[child_task_id]["result"]
            for child_task_id in group_record["child_task_ids"]
        ]
        task_record["result"] = {
            "status": "ok",
            "group_id": group_id,
            "merged_children": len(child_results),
            "child_results": child_results,
            "worker_id": worker_id,
        }
        self._set_task_state(task_record, "SUCCESS", stage="done", worker_id=worker_id)
        self.celery_processed_total += 1

        parent_task = self.celery_tasks[group_record["parent_task_id"]]
        parent_task["result"] = {
            "status": "ok",
            "group_id": group_id,
            "child_task_ids": group_record["child_task_ids"],
            "callback_task_id": task_record["task_id"],
            "merged_children": len(child_results),
        }
        self._set_task_state(parent_task, "SUCCESS", stage="done", worker_id=worker_id)

    async def _handle_group_child_success(self, task_record: dict) -> None:
        group_id = task_record["group_id"]
        group_record = self.celery_groups[group_id]
        if task_record["task_id"] not in group_record["completed_child_task_ids"]:
            group_record["completed_child_task_ids"].append(task_record["task_id"])

        completed = len(group_record["completed_child_task_ids"])
        parent_task = self.celery_tasks[group_record["parent_task_id"]]
        self._set_task_state(
            parent_task,
            "PROGRESS",
            stage="fanout_children_running",
            completed_children=completed,
            total_children=group_record["expected_children"],
        )

        if completed != group_record["expected_children"] or group_record["callback_task_id"] is not None:
            return

        callback_task = await self.submit_celery_job(
            work_ms=25,
            queue=group_record["callback_queue"],
            kind="fanout_callback",
            group_id=group_id,
        )
        group_record["callback_task_id"] = callback_task["task_id"]
        self._set_task_state(
            parent_task,
            "PROGRESS",
            stage="callback_queued",
            callback_task_id=callback_task["task_id"],
        )

    def _spawn_background_task(self, coro: Awaitable[None]) -> None:
        task = asyncio.create_task(coro)
        self.celery_background_tasks.add(task)
        task.add_done_callback(self.celery_background_tasks.discard)

    async def _requeue_celery_task(self, *, task_id: str, queue_name: str, delay_ms: int) -> None:
        await asyncio.sleep(delay_ms / 1000)
        await self.celery_broker_queues[queue_name].put(task_id)
        logger.info(
            "/tutorials/celery-redis/task %s: requeued queue=%s delay_ms=%s",
            task_id,
            queue_name,
            delay_ms,
        )

    def _next_celery_task_id(self) -> str:
        self.celery_next_task_id += 1
        return f"ctr-{self.celery_next_task_id:04d}"

    def _next_celery_group_id(self) -> str:
        self.celery_next_group_id += 1
        return f"group-{self.celery_next_group_id:04d}"

    def _append_history(self, task_record: dict, state: str, meta: dict) -> None:
        task_record["history"].append(
            {
                "state": state,
                "at_ms": round(time.time() * 1000),
                "meta": dict(meta),
            }
        )

    def _set_task_state(self, task_record: dict, state: str, **meta: object) -> None:
        task_record["state"] = state
        task_record["meta"].update(meta)
        task_record["updated_at_ms"] = round(time.time() * 1000)
        self._append_history(task_record, state=state, meta=task_record["meta"])

    def _successful_idempotency_keys(self) -> set[str]:
        return {
            task["idempotency_key"]
            for task in self.celery_tasks.values()
            if task.get("idempotency_key") and task.get("idempotency_completed")
        }

    async def start_workers(self) -> None:
        self.queue_worker_tasks.clear()
        for worker_id in range(1, self.queue_worker_count + 1):
            self.queue_worker_tasks.append(asyncio.create_task(self.queue_worker(worker_id)))

        self.celery_worker_tasks.clear()
        for queue_name, worker_id in self.celery_worker_plan:
            self.celery_worker_tasks.append(
                asyncio.create_task(self.celery_worker(queue_name=queue_name, worker_id=worker_id))
            )

    async def stop_workers(self) -> None:
        for task in [*self.queue_worker_tasks, *self.celery_worker_tasks]:
            task.cancel()
        if self.queue_worker_tasks or self.celery_worker_tasks:
            await asyncio.gather(
                *self.queue_worker_tasks,
                *self.celery_worker_tasks,
                return_exceptions=True,
            )
        self.queue_worker_tasks.clear()
        self.celery_worker_tasks.clear()

        background_tasks = list(self.celery_background_tasks)
        for task in background_tasks:
            task.cancel()
        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)
        self.celery_background_tasks.clear()

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
            "worker_tasks_running": sum(not task.done() for task in self.queue_worker_tasks),
            "enqueued_total": self.queue_enqueued_total,
            "processed_total": self.queue_processed_total,
            "failed_total": self.queue_failed_total,
        }

    async def submit_celery_job(
        self,
        *,
        work_ms: int,
        queue: str,
        fail_until_attempt: int = 0,
        idempotency_key: str | None = None,
        kind: str = "job",
        group_id: str | None = None,
    ) -> dict:
        if queue not in self.celery_broker_queues:
            raise HTTPException(status_code=422, detail=f"Unknown Celery tutorial queue: {queue}")

        task_id = self._next_celery_task_id()
        task_record = {
            "task_id": task_id,
            "kind": kind,
            "queue": queue,
            "state": "PENDING",
            "attempts": 0,
            "fail_until_attempt": fail_until_attempt,
            "idempotency_key": idempotency_key,
            "idempotency_completed": False,
            "work_ms": work_ms,
            "group_id": group_id,
            "created_at_ms": round(time.time() * 1000),
            "updated_at_ms": round(time.time() * 1000),
            "result": None,
            "meta": {
                "stage": "queued",
                "queue": queue,
                "kind": kind,
            },
            "history": [],
            "stage_names": ["fetching", "processing", "storing"],
        }
        self._append_history(task_record, state="PENDING", meta=task_record["meta"])
        self.celery_tasks[task_id] = task_record
        await self.celery_broker_queues[queue].put(task_id)
        self.celery_submitted_total += 1
        logger.info(
            "/tutorials/celery-redis/task %s: submitted queue=%s kind=%s fail_until_attempt=%s",
            task_id,
            queue,
            kind,
            fail_until_attempt,
        )
        return self.serialize_celery_task(task_id)

    async def submit_celery_fanout(
        self,
        *,
        num_tasks: int,
        work_ms: int,
        queue: str,
    ) -> dict:
        if queue not in self.celery_broker_queues:
            raise HTTPException(status_code=422, detail=f"Unknown Celery tutorial queue: {queue}")

        group_id = self._next_celery_group_id()
        parent_task_id = self._next_celery_task_id()
        parent_task = {
            "task_id": parent_task_id,
            "kind": "fanout_parent",
            "queue": queue,
            "state": "PENDING",
            "attempts": 0,
            "fail_until_attempt": 0,
            "idempotency_key": None,
            "idempotency_completed": False,
            "work_ms": work_ms,
            "group_id": group_id,
            "created_at_ms": round(time.time() * 1000),
            "updated_at_ms": round(time.time() * 1000),
            "result": None,
            "meta": {
                "stage": "queued",
                "queue": queue,
                "kind": "fanout_parent",
            },
            "history": [],
            "stage_names": [],
        }
        self._append_history(parent_task, state="PENDING", meta=parent_task["meta"])
        self.celery_tasks[parent_task_id] = parent_task

        child_task_ids: list[str] = []
        self.celery_groups[group_id] = {
            "group_id": group_id,
            "parent_task_id": parent_task_id,
            "child_task_ids": child_task_ids,
            "completed_child_task_ids": [],
            "expected_children": num_tasks,
            "callback_task_id": None,
            "callback_queue": queue,
        }

        self._set_task_state(
            parent_task,
            "PROGRESS",
            stage="fanout_queued",
            total_children=num_tasks,
            completed_children=0,
        )

        for _ in range(num_tasks):
            child_task = await self.submit_celery_job(
                work_ms=work_ms,
                queue=queue,
                kind="fanout_child",
                group_id=group_id,
            )
            child_task_ids.append(child_task["task_id"])

        return {
            "group_id": group_id,
            "parent_task_id": parent_task_id,
            "child_task_ids": child_task_ids,
            "state": parent_task["state"],
        }

    def serialize_celery_task(self, task_id: str) -> dict:
        task = self.celery_tasks[task_id]
        return {
            "task_id": task["task_id"],
            "kind": task["kind"],
            "queue": task["queue"],
            "state": task["state"],
            "attempts": task["attempts"],
            "fail_until_attempt": task["fail_until_attempt"],
            "idempotency_key": task["idempotency_key"],
            "group_id": task["group_id"],
            "created_at_ms": task["created_at_ms"],
            "updated_at_ms": task["updated_at_ms"],
            "meta": dict(task["meta"]),
            "history": list(task["history"]),
            "result": task["result"],
        }

    def get_celery_task(self, task_id: str) -> dict:
        if task_id not in self.celery_tasks:
            raise HTTPException(status_code=404, detail=f"Unknown Celery tutorial task: {task_id}")
        return self.serialize_celery_task(task_id)

    def celery_queue_stats(self) -> dict:
        queue_sizes = {
            queue_name: queue.qsize()
            for queue_name, queue in self.celery_broker_queues.items()
        }
        state_counts: dict[str, int] = {}
        for task in self.celery_tasks.values():
            state_counts[task["state"]] = state_counts.get(task["state"], 0) + 1

        worker_counts: dict[str, int] = {}
        worker_running: dict[str, int] = {}
        for (queue_name, _worker_id), task in zip(
            self.celery_worker_plan,
            self.celery_worker_tasks,
            strict=False,
        ):
            worker_counts[queue_name] = worker_counts.get(queue_name, 0) + 1
            if not task.done():
                worker_running[queue_name] = worker_running.get(queue_name, 0) + 1

        return {
            "status": "ok",
            "queues": queue_sizes,
            "worker_counts": worker_counts,
            "workers_running": worker_running,
            "submitted_total": self.celery_submitted_total,
            "processed_total": self.celery_processed_total,
            "failed_total": self.celery_failed_total,
            "retry_total": self.celery_retry_total,
            "deduped_total": self.celery_deduped_total,
            "known_tasks": len(self.celery_tasks),
            "state_counts": state_counts,
        }

    async def publish_celery_beat_job(self, *, queue: str = "light", work_ms: int = 40) -> dict:
        task = await self.submit_celery_job(
            work_ms=work_ms,
            queue=queue,
            kind="beat_job",
        )
        task_record = self.celery_tasks[task["task_id"]]
        task_record["meta"]["published_by"] = "beat"
        self._append_history(task_record, state=task_record["state"], meta=task_record["meta"])
        return self.serialize_celery_task(task["task_id"])


def get_tutorial_runtime(request: Request) -> TutorialRuntime:
    return request.app.state.tutorial_runtime
