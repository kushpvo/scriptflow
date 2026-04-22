from fastapi.testclient import TestClient


def test_validate_cron_valid():
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/validate/cron?expression=0+9+*+*+*")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["error"] is None


def test_validate_cron_invalid():
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/validate/cron?expression=not+a+cron")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["error"] is not None


def test_validate_cron_nextrun_valid():
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/validate/cron/nextrun?expression=0+9+*+*+*")
    assert response.status_code == 200
    data = response.json()
    assert data["nextrun"] is not None
    # Should be ISO format
    assert "T" in data["nextrun"]


def test_validate_cron_nextrun_invalid():
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/validate/cron/nextrun?expression=bad+expression")
    assert response.status_code == 200
    data = response.json()
    assert data["nextrun"] is None