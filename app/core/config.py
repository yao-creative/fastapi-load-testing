"""
Configuration skeleton for the tutorial track.

Values can be overridden using environment variables for real deployments.
"""

from dataclasses import dataclass
from os import getenv


@dataclass(slots=True)
class Settings:
    # Celery/Redis configuration
    redis_host: str = getenv("REDIS_HOST", "localhost")
    redis_port: int = int(getenv("REDIS_PORT", "6379"))
    redis_db: int = int(getenv("REDIS_DB", "0"))

    default_celery_queue: str = getenv("DEFAULT_CELERY_QUEUE", "jobs")
    heavy_celery_queue: str = getenv("HEAVY_CELERY_QUEUE", "pipelines")
    periodic_celery_queue: str = getenv("PERIODIC_CELERY_QUEUE", "periodic")

    @property
    def redis_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def redis_result_backend_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_task_queues(self) -> list[str]:
        return [
            self.default_celery_queue,
            self.heavy_celery_queue,
            self.periodic_celery_queue,
        ]

    # For later: optional beat schedule intervals can be added as settings fields.


settings = Settings()
