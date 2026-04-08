import os

from locust import HttpUser, between, task


class ApiUser(HttpUser):
    """
    Minimal Locust user hitting /health.

    TODO (you implement): add tasks for each endpoint variant and tune weights.
    """

    wait_time = between(0.1, 0.5)

    # In docker-compose we set LOCUST_HOST=http://api:8000
    # Locust also accepts -H / --host from CLI; env var is simplest.

    @task(10)
    def health(self):
        self.client.get("/health")

    # TODO (you implement): asyncio-variation tasks
    #
    # @task
    # def sleep_blocking(self):
    #     self.client.get("/sleep/blocking")
    #
    # @task
    # def sleep_async(self):
    #     self.client.get("/sleep/async")
    #
    # @task
    # def cpu_inline(self):
    #     self.client.get("/cpu/inline")
    #
    # @task
    # def cpu_to_thread(self):
    #     self.client.get("/cpu/to-thread")
    #
    # @task
    # def upstream_sync(self):
    #     self.client.get("/upstream/sync")
    #
    # @task
    # def upstream_async(self):
    #     self.client.get("/upstream/async")
    #
    # @task
    # def fanout_sequential(self):
    #     self.client.get("/fanout/sequential")
    #
    # @task
    # def fanout_gather(self):
    #     self.client.get("/fanout/gather")


def _debug_locust_host():
    # Helpful when running Locust outside compose.
    host = os.getenv("LOCUST_HOST")
    if host:
        return host
    return None

