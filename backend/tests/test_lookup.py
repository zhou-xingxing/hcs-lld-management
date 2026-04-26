"""IP Lookup tests."""

HEADERS = {"X-Operator": "test-operator"}


def _setup_data(client):
    """Create a region with an IP allocation for lookup tests."""
    r = client.post("/api/regions", json={"name": "TestRegion"}, headers=HEADERS).json()
    pt = client.post(
        "/api/network-plane-types", json={"name": "管理平面"}, headers=HEADERS
    ).json()
    plane_resp = client.post(
        f"/api/regions/{r['id']}/planes",
        json={"plane_type_id": pt["id"], "cidr": "10.0.0.0/22"},
        headers=HEADERS,
    )
    plane_id = plane_resp.json()["id"]
    client.post(
        f"/api/regions/{r['id']}/allocations",
        json={"plane_type_id": pt["id"], "plane_id": plane_id, "ip_range": "10.0.0.0/24"},
        headers=HEADERS,
    )
    return r, pt


def test_lookup_by_ip(client):
    _setup_data(client)
    resp = client.get("/api/lookup?q=10.0.0.5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["results"][0]["ip_range"] == "10.0.0.0/24"


def test_lookup_exact_cidr(client):
    _setup_data(client)
    resp = client.get("/api/lookup?q=10.0.0.0/24")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


def test_lookup_overlap_cidr(client):
    _setup_data(client)
    resp = client.get("/api/lookup?q=10.0.0.0/25&exact=false")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


def test_lookup_no_match(client):
    _setup_data(client)
    resp = client.get("/api/lookup?q=192.168.1.1")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_lookup_invalid_query(client):
    resp = client.get("/api/lookup?q=not-an-ip")
    assert resp.status_code == 400
