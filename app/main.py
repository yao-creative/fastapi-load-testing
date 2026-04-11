from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.tutorial_runtime import TutorialRuntime


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = TutorialRuntime()
    app.state.tutorial_runtime = runtime
    await runtime.start_workers()
    try:
        yield
    finally:
        await runtime.stop_workers()


def create_app() -> FastAPI:
    app = FastAPI(
        title="fastapi-load-testing",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(api_router)
    return app


app = create_app()
