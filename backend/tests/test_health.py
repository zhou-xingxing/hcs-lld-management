"""Health endpoint tests."""


def test_health_returns_200(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_health_body(client):
    resp = client.get("/api/health")
    assert resp.json() == {"status": "ok"}
