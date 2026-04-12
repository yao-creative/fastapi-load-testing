import time

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint():
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tutorial_routes_moved_under_prefix_and_legacy_path_removed():
    with TestClient(create_app()) as client:
        new_response = client.get("/tutorials/async/sleep/async", params={"seconds": 0})
        old_response = client.get("/sleep/async", params={"seconds": 0})

    assert new_response.status_code == 200
    assert new_response.json() == {"status": "ok"}
    assert old_response.status_code == 404


def test_queue_runtime_workers_and_stats():
    with TestClient(create_app()) as client:
        response = client.get("/tutorials/async/queue/stats")

    assert response.status_code == 200
    assert response.json()["worker_count"] == 2
    assert response.json()["worker_tasks_running"] == 2


def test_queue_drain_processes_jobs():
    with TestClient(create_app()) as client:
        drain_response = client.post(
            "/tutorials/async/queue/drain",
            params={"n": 2, "work_ms": 1},
        )
        stats_response = client.get("/tutorials/async/queue/stats")

    assert drain_response.status_code == 200
    assert drain_response.json()["enqueued"] == 2
    assert drain_response.json()["queue_size"] == 0
    assert stats_response.status_code == 200
    assert stats_response.json()["processed_total"] == 2


def test_timeout_endpoint_reports_completion_and_timeout():
    with TestClient(create_app()) as client:
        completed = client.get(
            "/tutorials/async/timeout/slow",
            params={"delay_ms": 10, "timeout_ms": 50},
        )
        timed_out = client.get(
            "/tutorials/async/timeout/slow",
            params={"delay_ms": 50, "timeout_ms": 10},
        )

    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert timed_out.status_code == 200
    assert timed_out.json()["status"] == "timed_out"


def test_fail_task_validation_still_returns_422():
    with TestClient(create_app()) as client:
        response = client.get(
            "/tutorials/async/fanout/gather-fail",
            params={"num_tasks": 2, "fail_task": 3},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "fail_task must be between 1 and num_tasks (2)"


def _wait_for_celery_task_state(
    client: TestClient,
    task_id: str,
    *,
    expected_state: str,
    timeout_s: float = 2.0,
) -> dict:
    deadline = time.time() + timeout_s
    last_payload = {}
    while time.time() < deadline:
        response = client.get(f"/tutorials/celery-redis/jobs/{task_id}")
        assert response.status_code == 200
        last_payload = response.json()
        if last_payload["state"] == expected_state:
            return last_payload
        time.sleep(0.02)

    raise AssertionError(f"Task {task_id} did not reach {expected_state}: {last_payload}")


def test_celery_tutorial_submit_and_poll_success():
    with TestClient(create_app()) as client:
        submit_response = client.post(
            "/tutorials/celery-redis/jobs/submit",
            params={"work_ms": 15, "queue": "light"},
        )
        task_id = submit_response.json()["task_id"]
        task_payload = _wait_for_celery_task_state(client, task_id, expected_state="SUCCESS")

    assert submit_response.status_code == 202
    assert task_payload["queue"] == "light"
    assert task_payload["result"]["status"] == "ok"


def test_celery_tutorial_retry_eventually_succeeds():
    with TestClient(create_app()) as client:
        submit_response = client.post(
            "/tutorials/celery-redis/jobs/submit",
            params={"work_ms": 10, "queue": "light", "fail_until_attempt": 1},
        )
        task_id = submit_response.json()["task_id"]
        task_payload = _wait_for_celery_task_state(client, task_id, expected_state="SUCCESS")

    assert submit_response.status_code == 202
    assert task_payload["attempts"] >= 2
    assert any(entry["state"] == "RETRY" for entry in task_payload["history"])


def test_celery_tutorial_fanout_runs_callback():
    with TestClient(create_app()) as client:
        fanout_response = client.post(
            "/tutorials/celery-redis/jobs/fanout",
            params={"num_tasks": 3, "work_ms": 10, "queue": "heavy"},
        )
        parent_task_id = fanout_response.json()["parent_task_id"]
        parent_payload = _wait_for_celery_task_state(client, parent_task_id, expected_state="SUCCESS")
        stats_response = client.get("/tutorials/celery-redis/queues/stats")

    assert fanout_response.status_code == 202
    assert parent_payload["result"]["merged_children"] == 3
    assert stats_response.status_code == 200
    assert stats_response.json()["known_tasks"] >= 5
