"""IP Allocation CRUD and overlap detection tests."""
import json

HEADERS = {"X-Operator": "test-operator"}


def _setup_region_and_plane(client):
    """Helper: create Region, PlaneType, enable root plane with CIDR, and return (region, pt, plane_id)."""
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
    return r, pt, plane_id


def _make_alloc_data(pt_id: str, plane_id: str, ip_range: str, **kwargs):
    data = {
        "plane_type_id": pt_id,
        "plane_id": plane_id,
        "ip_range": ip_range,
    }
    data.update(kwargs)
    return data


def test_create_allocation(client):
    region, pt, plane_id = _setup_region_and_plane(client)
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json=_make_alloc_data(pt["id"], plane_id, "10.0.0.0/24",
                              vlan_id=100, gateway="10.0.0.1",
                              purpose="Test allocation", status="active"),
        headers=HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ip_range"] == "10.0.0.0/24"
    assert data["vlan_id"] == 100


def test_create_overlapping_allocation_returns_409(client):
    region, pt, plane_id = _setup_region_and_plane(client)
    client.post(
        f"/api/regions/{region['id']}/allocations",
        json=_make_alloc_data(pt["id"], plane_id, "10.0.0.0/24"),
        headers=HEADERS,
    )
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json=_make_alloc_data(pt["id"], plane_id, "10.0.0.0/25"),
        headers=HEADERS,
    )
    assert resp.status_code == 409


def test_create_allocation_invalid_cidr(client):
    region, pt, plane_id = _setup_region_and_plane(client)
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json=_make_alloc_data(pt["id"], plane_id, "not-a-cidr"),
        headers=HEADERS,
    )
    assert resp.status_code == 409
    assert "无效的 CIDR" in resp.json()["detail"]


def test_update_allocation(client):
    region, pt, plane_id = _setup_region_and_plane(client)
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json=_make_alloc_data(pt["id"], plane_id, "10.0.0.0/24"),
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
    region, pt, plane_id = _setup_region_and_plane(client)
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json=_make_alloc_data(pt["id"], plane_id, "10.0.0.0/24"),
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
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json=_make_alloc_data(pt["id"], "nonexistent-plane", "10.0.0.0/24"),
        headers=HEADERS,
    )
    assert resp.status_code == 409
    assert "不存在" in resp.json()["detail"]


def test_allocation_outside_plane_cidr(client):
    """IP 段超出平面 CIDR 范围应报错。"""
    region, pt, plane_id = _setup_region_and_plane(client)
    # 平面 CIDR 为 10.0.0.0/22，IP 段 192.168.0.0/24 不在范围内
    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json=_make_alloc_data(pt["id"], plane_id, "192.168.0.0/24"),
        headers=HEADERS,
    )
    assert resp.status_code == 409
    assert "超出" in resp.json()["detail"]
