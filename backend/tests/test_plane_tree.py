"""网络平面全局树状结构测试。

覆盖：网络平面类型父子关系、Region 启用平面、CIDR 约束校验、树形结构查询、级联删除。
"""


def _create_plane_type(client, admin_headers, name, parent_id=None):
    """创建网络平面类型。"""
    payload = {"name": name}
    if parent_id:
        payload["parent_id"] = parent_id
    response = client.post("/api/network-plane-types", json=payload, headers=admin_headers)
    return response


def _setup(client, admin_headers, user_headers_factory):
    """创建 Region 和根 PlaneType，返回 (region, pt, user_headers)。"""
    region = client.post("/api/regions", json={"name": "TestRegion"}, headers=admin_headers).json()
    pt = _create_plane_type(client, admin_headers, "管理平面").json()
    return region, pt, user_headers_factory([region["id"]])


def _enable_plane(client, region_id, pt_id, cidr, user_headers):
    """启用 Region 网络平面并返回响应。"""
    return client.post(
        f"/api/regions/{region_id}/planes",
        json={"plane_type_id": pt_id, "cidr": cidr},
        headers=user_headers,
    )


def test_create_root_plane_with_cidr(client, admin_headers, user_headers_factory):
    """创建根平面时传入 CIDR，校验字段正确返回。"""
    region, pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    resp = _enable_plane(client, region["id"], pt["id"], "10.0.0.0/22", user_headers)

    assert resp.status_code == 201
    data = resp.json()
    assert data["cidr"] == "10.0.0.0/22"
    assert data["parent_id"] is None
    assert data["plane_type_parent_id"] is None
    assert data["updated_at"]


def test_create_root_plane_duplicate(client, admin_headers, user_headers_factory):
    """同一 (region, plane_type) 不能重复启用。"""
    region, pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    _enable_plane(client, region["id"], pt["id"], "10.0.0.0/22", user_headers)
    resp = _enable_plane(client, region["id"], pt["id"], "10.0.0.0/22", user_headers)

    assert resp.status_code == 409
    assert "已在 Region 中启用" in resp.json()["detail"]


def test_create_root_plane_invalid_cidr(client, admin_headers, user_headers_factory):
    """创建根平面时传入无效 CIDR 应报错。"""
    region, pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    resp = _enable_plane(client, region["id"], pt["id"], "invalid-cidr", user_headers)

    assert resp.status_code == 409
    assert "无效的 CIDR" in resp.json()["detail"]


def test_enable_child_plane(client, admin_headers, user_headers_factory):
    """正常启用子平面，校验 CIDR 在父范围内。"""
    region, root_pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    child_pt = _create_plane_type(client, admin_headers, "管理子平面A", parent_id=root_pt["id"]).json()
    root = _enable_plane(client, region["id"], root_pt["id"], "10.0.0.0/22", user_headers).json()

    resp = _enable_plane(client, region["id"], child_pt["id"], "10.0.0.0/24", user_headers)

    assert resp.status_code == 201
    data = resp.json()
    assert data["cidr"] == "10.0.0.0/24"
    assert data["parent_id"] == root["id"]
    assert data["plane_type_parent_id"] == root_pt["id"]
    assert data["updated_at"]


def test_enable_child_requires_parent_enabled(client, admin_headers, user_headers_factory):
    """子类型平面必须在父级已启用后才能启用。"""
    region, root_pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    child_pt = _create_plane_type(client, admin_headers, "管理子平面A", parent_id=root_pt["id"]).json()

    resp = _enable_plane(client, region["id"], child_pt["id"], "10.0.0.0/24", user_headers)

    assert resp.status_code == 409
    assert "父级网络平面尚未" in resp.json()["detail"]


def test_create_child_outside_parent(client, admin_headers, user_headers_factory):
    """子 CIDR 超出父范围应报错。"""
    region, root_pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    child_pt = _create_plane_type(client, admin_headers, "管理子平面A", parent_id=root_pt["id"]).json()
    _enable_plane(client, region["id"], root_pt["id"], "10.0.0.0/22", user_headers)

    resp = _enable_plane(client, region["id"], child_pt["id"], "192.168.0.0/24", user_headers)

    assert resp.status_code == 409
    assert "范围内" in resp.json()["detail"]


def test_create_child_sibling_overlap(client, admin_headers, user_headers_factory):
    """兄弟平面 CIDR 重叠应报错。"""
    region, root_pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    child_a = _create_plane_type(client, admin_headers, "管理子平面A", parent_id=root_pt["id"]).json()
    child_b = _create_plane_type(client, admin_headers, "管理子平面B", parent_id=root_pt["id"]).json()
    _enable_plane(client, region["id"], root_pt["id"], "10.0.0.0/22", user_headers)
    _enable_plane(client, region["id"], child_a["id"], "10.0.0.0/24", user_headers)

    resp = _enable_plane(client, region["id"], child_b["id"], "10.0.0.0/25", user_headers)

    assert resp.status_code == 409
    assert "重叠" in resp.json()["detail"]


def test_create_child_unrelated_ok(client, admin_headers, user_headers_factory):
    """兄弟平面 CIDR 不重叠时允许创建。"""
    region, root_pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    child_a = _create_plane_type(client, admin_headers, "管理子平面A", parent_id=root_pt["id"]).json()
    child_b = _create_plane_type(client, admin_headers, "管理子平面B", parent_id=root_pt["id"]).json()
    _enable_plane(client, region["id"], root_pt["id"], "10.0.0.0/22", user_headers)
    _enable_plane(client, region["id"], child_a["id"], "10.0.0.0/24", user_headers)

    resp = _enable_plane(client, region["id"], child_b["id"], "10.0.1.0/24", user_headers)

    assert resp.status_code == 201


def test_create_child_depth_exceeded(client, admin_headers):
    """全局类型树超过 3 级嵌套应报错。"""
    root = _create_plane_type(client, admin_headers, "根平面").json()
    child = _create_plane_type(client, admin_headers, "子平面", parent_id=root["id"]).json()
    grandchild = _create_plane_type(client, admin_headers, "孙平面", parent_id=child["id"]).json()

    resp = _create_plane_type(client, admin_headers, "四级平面", parent_id=grandchild["id"])

    assert resp.status_code == 409
    assert "最大嵌套层级" in resp.json()["detail"]


def test_get_plane_tree(client, admin_headers, user_headers_factory):
    """验证 GET /regions/{rid}/planes 返回由全局类型树派生的 Region 平面树。"""
    region, root_pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    child_a = _create_plane_type(client, admin_headers, "管理子平面A", parent_id=root_pt["id"]).json()
    child_b = _create_plane_type(client, admin_headers, "管理子平面B", parent_id=root_pt["id"]).json()
    grandchild = _create_plane_type(client, admin_headers, "管理孙平面", parent_id=child_a["id"]).json()

    _enable_plane(client, region["id"], root_pt["id"], "10.0.0.0/22", user_headers)
    _enable_plane(client, region["id"], child_a["id"], "10.0.0.0/24", user_headers)
    _enable_plane(client, region["id"], child_b["id"], "10.0.1.0/24", user_headers)
    _enable_plane(client, region["id"], grandchild["id"], "10.0.0.0/25", user_headers)

    resp = client.get(f"/api/regions/{region['id']}/planes", headers=user_headers)

    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 1
    assert tree[0]["cidr"] == "10.0.0.0/22"
    assert tree[0]["updated_at"]
    assert len(tree[0]["children"]) == 2
    child_a_node = next(node for node in tree[0]["children"] if node["plane_type_id"] == child_a["id"])
    assert child_a_node["children"][0]["cidr"] == "10.0.0.0/25"


def test_create_allocation_in_child_plane(client, admin_headers, user_headers_factory):
    """在子平面下创建 IP 分配，并校验 CIDR 在子平面 CIDR 范围内。"""
    region, root_pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    child_pt = _create_plane_type(client, admin_headers, "管理子平面A", parent_id=root_pt["id"]).json()
    _enable_plane(client, region["id"], root_pt["id"], "10.0.0.0/22", user_headers)
    child = _enable_plane(client, region["id"], child_pt["id"], "10.0.0.0/24", user_headers).json()

    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json={"plane_type_id": child_pt["id"], "plane_id": child["id"], "ip_range": "10.0.0.0/25"},
        headers=user_headers,
    )

    assert resp.status_code == 201


def test_create_allocation_overlaps_child_plane(client, admin_headers, user_headers_factory):
    """IP 分配覆盖子平面 CIDR 应报错。"""
    region, root_pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    child_pt = _create_plane_type(client, admin_headers, "管理子平面A", parent_id=root_pt["id"]).json()
    root = _enable_plane(client, region["id"], root_pt["id"], "10.0.0.0/22", user_headers).json()
    _enable_plane(client, region["id"], child_pt["id"], "10.0.0.0/24", user_headers)

    resp = client.post(
        f"/api/regions/{region['id']}/allocations",
        json={"plane_type_id": root_pt["id"], "plane_id": root["id"], "ip_range": "10.0.0.0/24"},
        headers=user_headers,
    )

    assert resp.status_code == 409
    assert "重叠" in resp.json()["detail"]


def test_delete_parent_plane_cascades(client, admin_headers, user_headers_factory):
    """删除父平面后，子平面和 IP 分配也被级联删除。"""
    region, root_pt, user_headers = _setup(client, admin_headers, user_headers_factory)
    child_pt = _create_plane_type(client, admin_headers, "管理子平面A", parent_id=root_pt["id"]).json()
    root = _enable_plane(client, region["id"], root_pt["id"], "10.0.0.0/22", user_headers).json()
    child = _enable_plane(client, region["id"], child_pt["id"], "10.0.0.0/24", user_headers).json()

    client.post(
        f"/api/regions/{region['id']}/allocations",
        json={"plane_type_id": child_pt["id"], "plane_id": child["id"], "ip_range": "10.0.0.0/25"},
        headers=user_headers,
    )
    client.post(
        f"/api/regions/{region['id']}/allocations",
        json={"plane_type_id": root_pt["id"], "plane_id": root["id"], "ip_range": "10.0.1.0/24"},
        headers=user_headers,
    )

    resp = client.delete(f"/api/regions/{region['id']}/planes/{root['id']}", headers=user_headers)

    assert resp.status_code == 204
    tree_resp = client.get(f"/api/regions/{region['id']}/planes", headers=user_headers)
    assert len(tree_resp.json()) == 0
    alloc_resp = client.get(f"/api/regions/{region['id']}/allocations", headers=user_headers)
    assert alloc_resp.json()["total"] == 0


def test_delete_nonexistent_plane(client, admin_headers, user_headers_factory):
    """删除不存在的平面应返回 404。"""
    region, _, user_headers = _setup(client, admin_headers, user_headers_factory)
    resp = client.delete(f"/api/regions/{region['id']}/planes/nonexistent", headers=user_headers)
    assert resp.status_code == 404
