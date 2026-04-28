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


def test_update_plane_type_returns_404(client, admin_headers):
    response = client.put(
        "/api/network-plane-types/missing-plane-type",
        json={"name": "不存在"},
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_update_plane_type_rejects_invalid_parent_moves(client, admin_headers):
    root = client.post("/api/network-plane-types", json={"name": "根平面"}, headers=admin_headers).json()
    child = client.post(
        "/api/network-plane-types",
        json={"name": "子平面", "parent_id": root["id"]},
        headers=admin_headers,
    ).json()

    self_parent = client.put(
        f"/api/network-plane-types/{root['id']}",
        json={"parent_id": root["id"]},
        headers=admin_headers,
    )
    move_to_child = client.put(
        f"/api/network-plane-types/{root['id']}",
        json={"parent_id": child["id"]},
        headers=admin_headers,
    )
    missing_parent = client.put(
        f"/api/network-plane-types/{root['id']}",
        json={"parent_id": "missing-parent"},
        headers=admin_headers,
    )

    assert self_parent.status_code == 409
    assert "自身" in self_parent.json()["detail"]
    assert move_to_child.status_code == 409
    assert "子级" in move_to_child.json()["detail"]
    assert missing_parent.status_code == 409
    assert "父级网络平面类型不存在" in missing_parent.json()["detail"]


def test_update_plane_type_rejects_move_that_would_exceed_depth(client, admin_headers):
    root = client.post("/api/network-plane-types", json={"name": "根平面"}, headers=admin_headers).json()
    child = client.post(
        "/api/network-plane-types",
        json={"name": "子平面", "parent_id": root["id"]},
        headers=admin_headers,
    ).json()
    client.post(
        "/api/network-plane-types",
        json={"name": "孙平面", "parent_id": child["id"]},
        headers=admin_headers,
    )
    new_parent = client.post("/api/network-plane-types", json={"name": "新父平面"}, headers=admin_headers).json()

    response = client.put(
        f"/api/network-plane-types/{root['id']}",
        json={"parent_id": new_parent["id"]},
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert "最大嵌套层级" in response.json()["detail"]


def test_update_plane_type_rejects_parent_change_when_used_by_region(
    client,
    admin_headers,
    user_headers_factory,
):
    region = client.post("/api/regions", json={"name": "Region-A"}, headers=admin_headers).json()
    plane_type = client.post("/api/network-plane-types", json={"name": "业务平面"}, headers=admin_headers).json()
    new_parent = client.post("/api/network-plane-types", json={"name": "父平面"}, headers=admin_headers).json()
    user_headers = user_headers_factory([region["id"]])
    create_plane = client.post(
        f"/api/regions/{region['id']}/planes",
        json={"plane_type_id": plane_type["id"], "cidr": "10.20.0.0/24"},
        headers=user_headers,
    )
    assert create_plane.status_code == 201

    response = client.put(
        f"/api/network-plane-types/{plane_type['id']}",
        json={"parent_id": new_parent["id"]},
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert "已被 Region 使用" in response.json()["detail"]


def test_delete_plane_type_success_and_missing(client, admin_headers):
    created = client.post("/api/network-plane-types", json={"name": "可删除平面"}, headers=admin_headers).json()

    delete_response = client.delete(f"/api/network-plane-types/{created['id']}", headers=admin_headers)
    missing_response = client.delete("/api/network-plane-types/missing-plane-type", headers=admin_headers)

    assert delete_response.status_code == 204
    assert missing_response.status_code == 404


def test_delete_plane_type_rejects_child_types(client, admin_headers):
    parent = client.post("/api/network-plane-types", json={"name": "父平面"}, headers=admin_headers).json()
    child_response = client.post(
        "/api/network-plane-types",
        json={"name": "子平面", "parent_id": parent["id"]},
        headers=admin_headers,
    )
    assert child_response.status_code == 201

    response = client.delete(f"/api/network-plane-types/{parent['id']}", headers=admin_headers)

    assert response.status_code == 409
    assert "child type" in response.json()["detail"]


def test_delete_plane_type_rejects_region_usage(client, admin_headers, user_headers_factory):
    region = client.post("/api/regions", json={"name": "Region-A"}, headers=admin_headers).json()
    plane_type = client.post("/api/network-plane-types", json={"name": "使用中平面"}, headers=admin_headers).json()
    user_headers = user_headers_factory([region["id"]])
    create_plane = client.post(
        f"/api/regions/{region['id']}/planes",
        json={"plane_type_id": plane_type["id"], "cidr": "10.21.0.0/24"},
        headers=user_headers,
    )
    assert create_plane.status_code == 201

    response = client.delete(f"/api/network-plane-types/{plane_type['id']}", headers=admin_headers)

    assert response.status_code == 409
    assert "in use" in response.json()["detail"]
