"""Integration tests verifying the asynchronous simulation lifecycle."""
import asyncio
import pytest
from fastapi.testclient import TestClient


def test_simulation_dispatch_and_poll_status(client: TestClient):
    """Verify simulation dispatch returns 202 and status transitions through lifecycle."""
    # 1. Dispatch simulation
    dispatch_res = client.post(
        "/api/v1/agents/simulations",
        json={"name": "Lifecycle Test Run", "num_days": 2, "num_firms": 4},
    )
    assert dispatch_res.status_code == 202
    data = dispatch_res.json()
    assert "experiment_id" in data
    assert "task_id" in data
    assert data["status"] == "queued"
    exp_id = data["experiment_id"]

    # 2. Poll simulation status
    status_res = client.get(f"/api/v1/agents/simulations/{exp_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["experiment_id"] == exp_id
    assert status_data["status"] in ("QUEUED", "RUNNING", "COMPLETED")


def test_simulation_cancellation(client: TestClient):
    """Verify cancelling an active simulation transitions status to CANCELLED."""
    # 1. Dispatch long simulation
    dispatch_res = client.post(
        "/api/v1/agents/simulations",
        json={"name": "Cancellation Test Run", "num_days": 100, "num_firms": 16},
    )
    assert dispatch_res.status_code == 202
    exp_id = dispatch_res.json()["experiment_id"]

    # 2. Cancel simulation
    cancel_res = client.post(f"/api/v1/agents/simulations/{exp_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # 3. Verify status reflects CANCELLED
    status_res = client.get(f"/api/v1/agents/simulations/{exp_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "CANCELLED"


def test_simulation_cancel_nonexistent_returns_404(client: TestClient):
    """Verify cancelling a non-existent simulation returns 404."""
    res = client.post("/api/v1/agents/simulations/exp_nonexistent_9999/cancel")
    assert res.status_code == 404


def test_agents_overview_metrics(client: TestClient):
    """Verify overview endpoint reports tracked metrics."""
    res = client.get("/api/v1/agents")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "agent_simulation_engine"
    assert "active_simulations" in data
    assert "total_tracked_tasks" in data
