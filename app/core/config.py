"""
Configuration skeleton for the tutorial track.

Now uses Pydantic BaseSettings for proper config management.

Values can be overridden using environment variables for real deployments.
"""

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # Celery/Redis configuration
    redis_host: str = Field("localhost", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_db: int = Field(0, env="REDIS_DB")

    default_celery_queue: str = Field("light", env="DEFAULT_CELERY_QUEUE")
    heavy_celery_queue: str = Field("heavy", env="HEAVY_CELERY_QUEUE")

    @property
    def redis_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def redis_result_backend_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_task_queues(self) -> list[str]:
        return [self.default_celery_queue, self.heavy_celery_queue]

    # For later: optional beat schedule intervals can be added as settings fields.


settings = Settings()