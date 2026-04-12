from fastapi import APIRouter

from app.api.system import router as system_router
from app.api.tutorials_async import router as tutorials_async_router
from app.api.tutorials_celery_redis import router as tutorials_celery_redis_router


api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(tutorials_async_router)
api_router.include_router(tutorials_celery_redis_router)
