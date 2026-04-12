"""
Worker-entrypoint notes.

This file exists so you have one obvious place to document or add worker-specific
bootstrap code later.
"""


# TODO: if you need worker bootstrap hooks, add them here.
# TODO: keep the actual Celery app import in `app/core/celery_app.py`.
# TODO: document the worker command you expect to run from Docker Compose.


from app.core.celery_app import celery_app

if __name__ == "__main__":
    celery_app.worker_main()