def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_app_has_openapi(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/api/health" in paths
