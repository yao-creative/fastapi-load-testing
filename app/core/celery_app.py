"""
Celery app skeleton for the tutorial track.

This file is intentionally not wired to a real Celery dependency yet.
Use it as the place where you will later:

- import and construct the Celery application
- configure broker and result backend URLs
- define task routing and default queues
- expose one stable import path for workers and beat

Suggested final import path:
- `app.core.celery_app:celery_app`
"""

from celery import Celery
from core.config import settings

# TODO: add `from celery import Celery` after you decide to install Celery.
# TODO: create `celery_app = Celery(...)`.
# TODO: set broker URL, result backend URL, and task serializer settings here.
# TODO: add `task_routes` or queue declarations once you reach the routing exercise.
# TODO: keep this file small; task functions should live in `app/tasks/`, not here.


def celery_app_import_path() -> str:
    """
    Stable string to reference from docs, worker commands, and later compose setup.
    """
    celery_app = Celery(
        broker=settings.redis_broker_url,
        backend=settings.redis_result_backend_url,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )

    celery_app.conf.task_routes = {
        "app.tasks.jobs.*": {"queue": "jobs"},
        "app.tasks.pipelines.*": {"queue": "pipelines"},
        "app.tasks.periodic.*": {"queue": "periodic"},
    }
    return celery_app
