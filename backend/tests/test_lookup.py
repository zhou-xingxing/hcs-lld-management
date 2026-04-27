"""IP Lookup tests."""

def _setup_data(client, admin_headers, user_headers_factory):
    """Create a region with an IP allocation for lookup tests."""
    r = client.post("/api/regions", json={"name": "TestRegion"}, headers=admin_headers).json()
    pt = client.post(
        "/api/network-plane-types", json={"name": "管理平面"}, headers=admin_headers
    ).json()
    user_headers = user_headers_factory([r["id"]])
    plane_resp = client.post(
        f"/api/regions/{r['id']}/planes",
        json={"plane_type_id": pt["id"], "cidr": "10.0.0.0/22"},
        headers=user_headers,
    )
    plane_id = plane_resp.json()["id"]
    client.post(
        f"/api/regions/{r['id']}/allocations",
        json={"plane_type_id": pt["id"], "plane_id": plane_id, "ip_range": "10.0.0.0/24"},
        headers=user_headers,
    )
    return r, pt, user_headers


def test_lookup_by_ip(client, admin_headers, user_headers_factory):
    _, _, user_headers = _setup_data(client, admin_headers, user_headers_factory)
    resp = client.get("/api/lookup?q=10.0.0.5", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["results"][0]["ip_range"] == "10.0.0.0/24"


def test_lookup_exact_cidr(client, admin_headers, user_headers_factory):
    _, _, user_headers = _setup_data(client, admin_headers, user_headers_factory)
    resp = client.get("/api/lookup?q=10.0.0.0/24", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


def test_lookup_overlap_cidr(client, admin_headers, user_headers_factory):
    _, _, user_headers = _setup_data(client, admin_headers, user_headers_factory)
    resp = client.get("/api/lookup?q=10.0.0.0/25&exact=false", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


def test_lookup_no_match(client, admin_headers, user_headers_factory):
    _, _, user_headers = _setup_data(client, admin_headers, user_headers_factory)
    resp = client.get("/api/lookup?q=192.168.1.1", headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_lookup_invalid_query(client, admin_headers):
    resp = client.get("/api/lookup?q=not-an-ip", headers=admin_headers)
    assert resp.status_code == 400
