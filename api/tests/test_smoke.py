"""Minimal smoke tests for API service."""


def test_health_endpoint_returns_ok() -> None:
    # Import inside the test to ensure environment variables are already set
    from fastapi.testclient import TestClient
    from dnd_helper_api.main import app

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


