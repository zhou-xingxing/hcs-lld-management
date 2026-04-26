"""网络平面多级树状结构测试。

覆盖：根平面创建、子平面创建、CIDR 约束校验、树形结构查询、级联删除。
"""

HEADERS = {"X-Operator": "test-operator"}


def _setup(client):
    """创建 Region 和 PlaneType，返回 (region, pt)。"""
    r = client.post("/api/regions", json={"name": "TestRegion"}, headers=HEADERS).json()
    pt = client.post(
        "/api/network-plane-types", json={"name": "管理平面"}, headers=HEADERS
    ).json()
    return r, pt


# ========== 根平面创建 ==========


def test_create_root_plane_with_cidr(client):
    """创建根平面时传入 CIDR，校验字段正确返回。"""
    r, pt = _setup(client)
    resp = client.post(
        f"/api/regions/{r['id']}/planes",
        json={"plane_type_id": pt["id"], "cidr": "10.0.0.0/22"},
        headers=HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["cidr"] == "10.0.0.0/22"
    assert data["parent_id"] is None


def test_create_root_plane_duplicate(client):
    """同一 (region, plane_type) 不能创建多个根平面。"""
    r, pt = _setup(client)
    client.post(
        f"/api/regions/{r['id']}/planes",
        json={"plane_type_id": pt["id"], "cidr": "10.0.0.0/22"},
        headers=HEADERS,
    )
    resp = client.post(
        f"/api/regions/{r['id']}/planes",
        json={"plane_type_id": pt["id"], "cidr": "10.0.0.0/22"},
        headers=HEADERS,
    )
    assert resp.status_code == 409
    assert "已存在根节点" in resp.json()["detail"]


def test_create_root_plane_invalid_cidr(client):
    """创建根平面时传入无效 CIDR 应报错。"""
    r, pt = _setup(client)
    resp = client.post(
        f"/api/regions/{r['id']}/planes",
        json={"plane_type_id": pt["id"], "cidr": "invalid-cidr"},
        headers=HEADERS,
    )
    assert resp.status_code == 409
    assert "无效的 CIDR" in resp.json()["detail"]


# ========== 子平面创建 ==========


def _create_root_plane(client, region_id, pt_id):
    """Helper: 创建根平面并返回其 ID。"""
    resp = client.post(
        f"/api/regions/{region_id}/planes",
        json={"plane_type_id": pt_id, "cidr": "10.0.0.0/22"},
        headers=HEADERS,
    )
    return resp.json()["id"]


def test_create_child_plane(client):
    """正常创建子平面，校验 CIDR 在父范围内。"""
    r, pt = _setup(client)
    parent_id = _create_root_plane(client, r["id"], pt["id"])

    # 子 CIDR 10.0.0.0/24 在父 CIDR 10.0.0.0/22 范围内
    resp = client.post(
        f"/api/regions/{r['id']}/planes/{parent_id}/children",
        json={"cidr": "10.0.0.0/24"},
        headers=HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["cidr"] == "10.0.0.0/24"
    assert data["parent_id"] == parent_id


def test_create_child_outside_parent(client):
    """子 CIDR 超出父范围应报错。"""
    r, pt = _setup(client)
    parent_id = _create_root_plane(client, r["id"], pt["id"])

    # 10.0.0.0/22 不包含 192.168.0.0/24
    resp = client.post(
        f"/api/regions/{r['id']}/planes/{parent_id}/children",
        json={"cidr": "192.168.0.0/24"},
        headers=HEADERS,
    )
    assert resp.status_code == 409
    assert "范围内" in resp.json()["detail"]


def test_create_child_sibling_overlap(client):
    """兄弟平面 CIDR 重叠应报错。"""
    r, pt = _setup(client)
    parent_id = _create_root_plane(client, r["id"], pt["id"])

    # 第一个子平面
    client.post(
        f"/api/regions/{r['id']}/planes/{parent_id}/children",
        json={"cidr": "10.0.0.0/24"},
        headers=HEADERS,
    )
    # 第二个子平面与第一个重叠
    resp = client.post(
        f"/api/regions/{r['id']}/planes/{parent_id}/children",
        json={"cidr": "10.0.0.0/25"},
        headers=HEADERS,
    )
    assert resp.status_code == 409
    assert "重叠" in resp.json()["detail"]


def test_create_child_unrelated_ok(client):
    """兄弟平面 CIDR 不重叠时允许创建。"""
    r, pt = _setup(client)
    parent_id = _create_root_plane(client, r["id"], pt["id"])

    client.post(
        f"/api/regions/{r['id']}/planes/{parent_id}/children",
        json={"cidr": "10.0.0.0/24"},
        headers=HEADERS,
    )
    # 10.0.1.0/24 与 10.0.0.0/24 不重叠，都在 10.0.0.0/22 内
    resp = client.post(
        f"/api/regions/{r['id']}/planes/{parent_id}/children",
        json={"cidr": "10.0.1.0/24"},
        headers=HEADERS,
    )
    assert resp.status_code == 201


def test_create_child_depth_exceeded(client):
    """超过 3 级嵌套应报错。"""
    r, pt = _setup(client)
    # 第1级: root
    root_id = _create_root_plane(client, r["id"], pt["id"])
    # 第2级: child
    resp = client.post(
        f"/api/regions/{r['id']}/planes/{root_id}/children",
        json={"cidr": "10.0.0.0/24"},
        headers=HEADERS,
    )
    child_id = resp.json()["id"]
    # 第3级: grandchild（允许）
    resp = client.post(
        f"/api/regions/{r['id']}/planes/{child_id}/children",
        json={"cidr": "10.0.0.0/25"},
        headers=HEADERS,
    )
    assert resp.status_code == 201
    grandchild_id = resp.json()["id"]
    # 第4级: 应报错（最多3级）
    resp = client.post(
        f"/api/regions/{r['id']}/planes/{grandchild_id}/children",
        json={"cidr": "10.0.0.128/26"},
        headers=HEADERS,
    )
    assert resp.status_code == 409
    assert "最大嵌套层级" in resp.json()["detail"]


# ========== 树形结构查询 ==========


def test_get_plane_tree(client):
    """验证 GET /regions/{rid}/planes 返回正确的树形结构。"""
    r, pt = _setup(client)
    root_id = _create_root_plane(client, r["id"], pt["id"])

    # 创建两个子平面
    resp1 = client.post(
        f"/api/regions/{r['id']}/planes/{root_id}/children",
        json={"cidr": "10.0.0.0/24"},
        headers=HEADERS,
    )
    child1_id = resp1.json()["id"]
    client.post(
        f"/api/regions/{r['id']}/planes/{root_id}/children",
        json={"cidr": "10.0.1.0/24"},
        headers=HEADERS,
    )
    # 在子平面下再创建孙子平面
    client.post(
        f"/api/regions/{r['id']}/planes/{child1_id}/children",
        json={"cidr": "10.0.0.0/25"},
        headers=HEADERS,
    )

    # 查询树形结构
    resp = client.get(f"/api/regions/{r['id']}/planes")
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 1  # 一个根
    assert tree[0]["cidr"] == "10.0.0.0/22"
    assert len(tree[0]["children"]) == 2  # 两个子平面
    assert tree[0]["children"][0]["children"][0]["cidr"] == "10.0.0.0/25"  # 孙子


# ========== IP 分配与平面层级 ==========


def test_create_allocation_in_child_plane(client):
    """在子平面下创建 IP 分配，并校验 CIDR 在子平面 CIDR 范围内。"""
    r, pt = _setup(client)
    root_id = _create_root_plane(client, r["id"], pt["id"])
    resp = client.post(
        f"/api/regions/{r['id']}/planes/{root_id}/children",
        json={"cidr": "10.0.0.0/24"},
        headers=HEADERS,
    )
    child_id = resp.json()["id"]

    # 在子平面下创建分配（在子平面 CIDR 内）
    resp = client.post(
        f"/api/regions/{r['id']}/allocations",
        json={"plane_type_id": pt["id"], "plane_id": child_id, "ip_range": "10.0.0.0/25"},
        headers=HEADERS,
    )
    assert resp.status_code == 201


def test_create_allocation_overlaps_child_plane(client):
    """IP 分配覆盖子平面 CIDR 应报错。"""
    r, pt = _setup(client)
    root_id = _create_root_plane(client, r["id"], pt["id"])
    client.post(
        f"/api/regions/{r['id']}/planes/{root_id}/children",
        json={"cidr": "10.0.0.0/24"},
        headers=HEADERS,
    )

    # 分配 10.0.0.0/24 与子平面 CIDR 完全重叠
    resp = client.post(
        f"/api/regions/{r['id']}/allocations",
        json={"plane_type_id": pt["id"], "plane_id": root_id, "ip_range": "10.0.0.0/24"},
        headers=HEADERS,
    )
    assert resp.status_code == 409
    assert "重叠" in resp.json()["detail"]


# ========== 级联删除 ==========


def test_delete_parent_plane_cascades(client):
    """删除父平面后，子平面和 IP 分配也被级联删除。"""
    r, pt = _setup(client)
    root_id = _create_root_plane(client, r["id"], pt["id"])

    # 创建子平面
    resp = client.post(
        f"/api/regions/{r['id']}/planes/{root_id}/children",
        json={"cidr": "10.0.0.0/24"},
        headers=HEADERS,
    )
    child_id = resp.json()["id"]

    # 在子平面和根平面下各创建一个分配
    client.post(
        f"/api/regions/{r['id']}/allocations",
        json={"plane_type_id": pt["id"], "plane_id": child_id, "ip_range": "10.0.0.0/25"},
        headers=HEADERS,
    )
    client.post(
        f"/api/regions/{r['id']}/allocations",
        json={"plane_type_id": pt["id"], "plane_id": root_id, "ip_range": "10.0.1.0/24"},
        headers=HEADERS,
    )

    # 删除根平面
    resp = client.delete(f"/api/regions/{r['id']}/planes/{root_id}", headers=HEADERS)
    assert resp.status_code == 204

    # 验证子平面也被删除
    tree_resp = client.get(f"/api/regions/{r['id']}/planes")
    assert len(tree_resp.json()) == 0

    # 验证所有分配也被删除
    alloc_resp = client.get(f"/api/regions/{r['id']}/allocations")
    assert alloc_resp.json()["total"] == 0


def test_delete_nonexistent_plane(client):
    """删除不存在的平面应返回 404。"""
    r, pt = _setup(client)
    resp = client.delete(f"/api/regions/{r['id']}/planes/nonexistent", headers=HEADERS)
    assert resp.status_code == 404
