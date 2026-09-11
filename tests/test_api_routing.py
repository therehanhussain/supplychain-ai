"""Test API Routing for Versioned (/api/v1/*) and Legacy Endpoints."""

from fastapi.testclient import TestClient


def test_v1_suppliers_api(client: TestClient):
    """Verify /api/v1/suppliers lists suppliers."""
    response = client.get("/api/v1/suppliers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "name" in data[0]
    assert "tier" in data[0]


def test_v1_inventory_api(client: TestClient):
    """Verify /api/v1/inventory lists items."""
    response = client.get("/api/v1/inventory")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "sku" in data[0]


def test_v1_orders_api(client: TestClient):
    """Verify /api/v1/orders lists orders."""
    response = client.get("/api/v1/orders")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_v1_shipments_api(client: TestClient):
    """Verify /api/v1/shipments lists shipments."""
    response = client.get("/api/v1/shipments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_v1_routes_topology_api(client: TestClient):
    """Verify /api/v1/routes/topology returns graph data."""
    response = client.get("/api/v1/routes/topology")
    assert response.status_code == 200
    data = response.json()
    assert "source" in data
    assert "relationships" in data


def test_v1_analytics_summary_api(client: TestClient):
    """Verify /api/v1/analytics/summary returns KPI metrics."""
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_suppliers" in data
    assert "active_orders" in data


def test_v1_simulation_dispatch_api(client: TestClient):
    """Verify /api/v1/agents/simulations returns 202 Accepted without blocking."""
    response = client.post("/api/v1/agents/simulations", json={"name": "Test Sim", "num_days": 2, "num_firms": 4})
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert "experiment_id" in data
    assert "task_id" in data


def test_legacy_experiments_endpoint(client: TestClient):
    """Verify legacy /api/experiments continues functioning for existing frontend."""
    response = client.get("/api/experiments")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)


def test_legacy_state_endpoint(client: TestClient):
    """Verify legacy /api/state/{fid} continues functioning."""
    response = client.get("/api/state/1")
    assert response.status_code == 200
