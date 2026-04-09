import os

from locust import HttpUser, between, task


SLEEP_SECONDS = int(os.getenv("LOCUST_SLEEP_SECONDS", "1"))


class ApiUser(HttpUser):
    """
    Mixed traffic profile.

    This is useful for demonstrating that one blocking endpoint can raise
    latency for unrelated requests like /health when the app runs with a
    single worker.
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
            "/sleep/blocking",
            params={"seconds": SLEEP_SECONDS},
            name="/sleep/blocking",
        )

    @task(1)
    def sleep_async(self):
        self.client.get(
            "/sleep/async",
            params={"seconds": SLEEP_SECONDS},
            name="/sleep/async",
        )


def _debug_locust_host():
    # Helpful when running Locust outside compose.
    host = os.getenv("LOCUST_HOST")
    if host:
        return host
    return None
