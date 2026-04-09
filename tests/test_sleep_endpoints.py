import asyncio
import time

def test_sleep_blocking_returns_ok(async_client_factory):
    async def scenario():
        async with async_client_factory() as client:
            response = await client.get("/sleep/blocking", params={"seconds": 0})
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    run(scenario())


def test_sleep_async_returns_ok(async_client_factory):
    async def scenario():
        async with async_client_factory() as client:
            response = await client.get("/sleep/async", params={"seconds": 0})
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    run(scenario())


def test_sleep_blocking_serializes_concurrent_requests(async_client_factory):
    async def scenario():
        async with async_client_factory() as client:
            started = time.perf_counter()
            responses = await asyncio.gather(
                client.get("/sleep/blocking", params={"seconds": 1}),
                client.get("/sleep/blocking", params={"seconds": 1}),
            )
            elapsed = time.perf_counter() - started
        return responses, elapsed

    responses, elapsed = run(scenario())

    assert all(response.status_code == 200 for response in responses)
    assert elapsed >= 1.9


def test_sleep_async_allows_concurrent_requests(async_client_factory):
    async def scenario():
        async with async_client_factory() as client:
            started = time.perf_counter()
            responses = await asyncio.gather(
                client.get("/sleep/async", params={"seconds": 1}),
                client.get("/sleep/async", params={"seconds": 1}),
            )
            elapsed = time.perf_counter() - started
        return responses, elapsed

    responses, elapsed = run(scenario())

    assert all(response.status_code == 200 for response in responses)
    assert elapsed < 1.2


def test_sleep_blocking_delays_unrelated_health_request(async_client_factory):
    async def scenario():
        async with async_client_factory() as client:
            started = time.perf_counter()
            blocking_task = asyncio.create_task(
                client.get("/sleep/blocking", params={"seconds": 1})
            )
            await asyncio.sleep(0.01)
            health_response = await client.get("/health")
            health_elapsed = time.perf_counter() - started
            blocking_response = await blocking_task
        return blocking_response, health_response, health_elapsed

    blocking_response, health_response, health_elapsed = run(scenario())

    assert blocking_response.status_code == 200
    assert health_response.status_code == 200
    assert health_elapsed >= 0.95


def test_sleep_async_does_not_delay_unrelated_health_request(async_client_factory):
    async def scenario():
        async with async_client_factory() as client:
            started = time.perf_counter()
            sleeping_task = asyncio.create_task(
                client.get("/sleep/async", params={"seconds": 1})
            )
            await asyncio.sleep(0.01)
            health_response = await client.get("/health")
            health_elapsed = time.perf_counter() - started
            sleeping_response = await sleeping_task
        return sleeping_response, health_response, health_elapsed

    sleeping_response, health_response, health_elapsed = run(scenario())

    assert sleeping_response.status_code == 200
    assert health_response.status_code == 200
    assert health_elapsed < 0.2
