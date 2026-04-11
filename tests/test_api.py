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
