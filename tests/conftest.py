import asyncio

import httpx
import pytest

from app.main import app


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def async_client_factory():
    def factory():
        transport = httpx.ASGITransport(app=app)
        return httpx.AsyncClient(transport=transport, base_url="http://testserver")

    return factory
