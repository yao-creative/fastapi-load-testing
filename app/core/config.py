"""
Configuration skeleton for the tutorial track.

Values can be overridden using environment variables for real deployments.
Load environment variables from an .env file if present.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from an .env file if provided.
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file, override=True)

class Settings(BaseSettings):
    # Celery/Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    default_celery_queue: str = "jobs"
    heavy_celery_queue: str = "pipelines"
    periodic_celery_queue: str = "periodic"

    model_config = SettingsConfigDict(
        env_file=str(env_file),
        env_file_encoding='utf-8'
    )

    @property
    def redis_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def redis_result_backend_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_task_queues(self) -> List[str]:
        return [
            self.default_celery_queue,
            self.heavy_celery_queue,
            self.periodic_celery_queue,
        ]

    # For later: optional beat schedule intervals can be added as settings fields.


settings = Settings()
