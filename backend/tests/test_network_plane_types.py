"""Network plane type API tests."""


def test_create_plane_type_with_private_and_vrf(client, admin_headers):
    response = client.post(
        "/api/network-plane-types",
        json={
            "name": "管理平面",
            "description": "管理网络",
            "is_private": True,
            "vrf": "vrf-mgmt",
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "管理平面"
    assert data["is_private"] is True
    assert data["vrf"] == "vrf-mgmt"
    assert data["updated_at"]


def test_update_plane_type_private_and_clear_vrf(client, admin_headers):
    created = client.post(
        "/api/network-plane-types",
        json={"name": "业务平面", "is_private": True, "vrf": "vrf-business"},
        headers=admin_headers,
    ).json()

    response = client.put(
        f"/api/network-plane-types/{created['id']}",
        json={"is_private": False, "vrf": None},
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_private"] is False
    assert data["vrf"] is None
    assert data["updated_at"]


def test_plane_type_defaults_private_to_false(client, admin_headers):
    response = client.post("/api/network-plane-types", json={"name": "存储平面"}, headers=admin_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["is_private"] is False
    assert data["vrf"] is None


def test_create_plane_type_with_parent(client, admin_headers):
    parent = client.post("/api/network-plane-types", json={"name": "父平面"}, headers=admin_headers).json()

    response = client.post(
        "/api/network-plane-types",
        json={"name": "子平面", "parent_id": parent["id"]},
        headers=admin_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["parent_id"] == parent["id"]
    assert data["parent_name"] == "父平面"
