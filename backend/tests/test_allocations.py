"""IP Allocation CRUD and overlap detection tests."""

HEADERS = {"X-Operator": "test-operator"}


def _setup_region_and_plane(client):
    """Helper: create Region, PlaneType, and enable plane."""
    r = client.post("/api/regions", json={"name": "TestRegion"}, headers=HEADERS).json()
    pt = client.post(
        "/api/network-plane-types", json={"name": "管理平面"}, headers=HEADERS
    ).json()
    client.post(
        f"/api/regions/{r['id']}/planes",
        json={"plane_type_id": pt["id"]},
        headers=HEADERS,
    )
    return r, pt


def test_create_allocation(client):
    region, pt = _setup_region_and_plane(client)
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json={
            "plane_type_id": pt["id"],
            "ip_range": "10.0.0.0/24",
            "vlan_id": 100,
            "gateway": "10.0.0.1",
            "purpose": "Test allocation",
            "status": "active",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ip_range"] == "10.0.0.0/24"
    assert data["vlan_id"] == 100


def test_create_overlapping_allocation_returns_409(client):
    region, pt = _setup_region_and_plane(client)
    client.post(
        f"/api/regions/{region['id']}/allocations",
        json={"plane_type_id": pt["id"], "ip_range": "10.0.0.0/24"},
        headers=HEADERS,
    )
    # Overlapping CIDR
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json={"plane_type_id": pt["id"], "ip_range": "10.0.0.0/25"},
        headers=HEADERS,
    )
    assert resp.status_code == 409


def test_create_allocation_invalid_cidr(client):
    region, pt = _setup_region_and_plane(client)
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json={"plane_type_id": pt["id"], "ip_range": "not-a-cidr"},
        headers=HEADERS,
    )
    # FastAPI/Pydantic won't validate CIDR at schema level (string),
    # but service layer will raise 409 with "Invalid CIDR"
    assert resp.status_code == 409
    assert "Invalid CIDR" in resp.json()["detail"]


def test_update_allocation(client):
    region, pt = _setup_region_and_plane(client)
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json={"plane_type_id": pt["id"], "ip_range": "10.0.0.0/24"},
        headers=HEADERS,
    )
    alloc_id = resp.json()["id"]

    resp = client.put(
        f"/api/allocations/{alloc_id}",
        json={"purpose": "Updated purpose", "vlan_id": 200},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["vlan_id"] == 200
    assert resp.json()["purpose"] == "Updated purpose"


def test_delete_allocation(client):
    region, pt = _setup_region_and_plane(client)
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json={"plane_type_id": pt["id"], "ip_range": "10.0.0.0/24"},
        headers=HEADERS,
    )
    alloc_id = resp.json()["id"]

    resp = client.delete(f"/api/allocations/{alloc_id}", headers=HEADERS)
    assert resp.status_code == 204

    resp = client.get(f"/api/allocations/{alloc_id}")
    assert resp.status_code == 404


def test_allocation_without_enabled_plane(client):
    """Cannot create allocation for a plane not enabled in the region."""
    region = client.post("/api/regions", json={"name": "R"}, headers=HEADERS).json()
    pt = client.post(
        "/api/network-plane-types", json={"name": "测试平面"}, headers=HEADERS
    ).json()
    # Don't enable the plane
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json={"plane_type_id": pt["id"], "ip_range": "10.0.0.0/24"},
        headers=HEADERS,
    )
    assert resp.status_code == 409
    assert "not enabled" in resp.json()["detail"]
