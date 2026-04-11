import os

from locust import HttpUser, between, task


SLEEP_SECONDS = int(os.getenv("LOCUST_SLEEP_SECONDS", "1"))


class ApiUser(HttpUser):
    """
    Mixed traffic profile.

    With a single Uvicorn worker, a blocking endpoint can raise latency for
    unrelated requests like /health. With multiple workers (see docker-compose),
    those effects change; compare runs with `--workers 1` vs `--workers 2`.
    """

    wait_time = between(0.1, 0.5)

    # In docker-compose we set LOCUST_HOST=http://api:8000
    # Locust also accepts -H / --host from CLI; env var is simplest.

    @task(10)
    def health(self):
        self.client.get("/health")

    @task(1)
    def sleep_blocking(self):
        self.client.get(
            "/tutorials/async/sleep/blocking",
            params={"seconds": SLEEP_SECONDS},
            name="/tutorials/async/sleep/blocking",
        )

    @task(1)
    def sleep_async(self):
        self.client.get(
            "/tutorials/async/sleep/async",
            params={"seconds": SLEEP_SECONDS},
            name="/tutorials/async/sleep/async",
        )


def _debug_locust_host():
    # Helpful when running Locust outside compose.
    host = os.getenv("LOCUST_HOST")
    if host:
        return host
    return None
