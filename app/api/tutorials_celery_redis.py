import logging

from fastapi import APIRouter, Depends, Query, status

from app.core.tutorial_runtime import TutorialRuntime, get_tutorial_runtime


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tutorials/celery-redis",
    tags=["tutorials-celery-redis"],
)


@router.post("/jobs/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_job(
    work_ms: int = Query(default=120, ge=1, le=60_000),
    queue: str = Query(default="light"),
    fail_until_attempt: int = Query(default=0, ge=0, le=5),
    idempotency_key: str | None = Query(default=None),
    runtime: TutorialRuntime = Depends(get_tutorial_runtime),
):
    # This mirrors the request-time "publish task to broker and return task_id"
    # pattern from the docs. The actual work is done later by the tutorial workers.
    task = await runtime.submit_celery_job(
        work_ms=work_ms,
        queue=queue,
        fail_until_attempt=fail_until_attempt,
        idempotency_key=idempotency_key,
    )
    logger.info(
        "/tutorials/celery-redis/jobs/submit: task_id=%s queue=%s fail_until_attempt=%s",
        task["task_id"],
        queue,
        fail_until_attempt,
    )
    return {
        "status": "accepted",
        "task_id": task["task_id"],
        "queue": queue,
        "status_url": f"/tutorials/celery-redis/jobs/{task['task_id']}",
    }


@router.get("/jobs/{task_id}")
async def get_job(
    task_id: str,
    runtime: TutorialRuntime = Depends(get_tutorial_runtime),
):
    # Celery users usually poll task state through the result backend. Here we
    # expose the same idea from the tutorial runtime's in-memory task store.
    return runtime.get_celery_task(task_id)


@router.post("/jobs/fanout", status_code=status.HTTP_202_ACCEPTED)
async def submit_fanout(
    num_tasks: int = Query(default=5, ge=1, le=50),
    work_ms: int = Query(default=60, ge=1, le=60_000),
    queue: str = Query(default="heavy"),
    runtime: TutorialRuntime = Depends(get_tutorial_runtime),
):
    fanout = await runtime.submit_celery_fanout(
        num_tasks=num_tasks,
        work_ms=work_ms,
        queue=queue,
    )
    logger.info(
        "/tutorials/celery-redis/jobs/fanout: parent_task_id=%s group_id=%s num_tasks=%s",
        fanout["parent_task_id"],
        fanout["group_id"],
        num_tasks,
    )
    return {
        "status": "accepted",
        "group_id": fanout["group_id"],
        "parent_task_id": fanout["parent_task_id"],
        "child_task_ids": fanout["child_task_ids"],
        "status_url": f"/tutorials/celery-redis/jobs/{fanout['parent_task_id']}",
    }


@router.post("/beat/tick", status_code=status.HTTP_202_ACCEPTED)
async def beat_tick(
    queue: str = Query(default="light"),
    work_ms: int = Query(default=40, ge=1, le=60_000),
    runtime: TutorialRuntime = Depends(get_tutorial_runtime),
):
    # Beat is the scheduler, not the worker. This endpoint simulates beat
    # publishing one scheduled task into the broker so you can inspect it.
    task = await runtime.publish_celery_beat_job(queue=queue, work_ms=work_ms)
    logger.info("/tutorials/celery-redis/beat/tick: task_id=%s queue=%s", task["task_id"], queue)
    return {
        "status": "accepted",
        "published_by": "beat",
        "task_id": task["task_id"],
        "queue": queue,
        "status_url": f"/tutorials/celery-redis/jobs/{task['task_id']}",
    }


@router.get("/queues/stats")
async def queue_stats(runtime: TutorialRuntime = Depends(get_tutorial_runtime)):
    return runtime.celery_queue_stats()
