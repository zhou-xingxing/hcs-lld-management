"""Region CRUD tests."""


REGION_DATA = {"name": "HCS华北-北京", "description": "Production region"}
HEADERS = {"X-Operator": "test-operator"}


def test_create_region(client):
    resp = client.post("/api/regions", json=REGION_DATA, headers=HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == REGION_DATA["name"]
    assert data["description"] == REGION_DATA["description"]
    assert "id" in data


def test_create_duplicate_region(client):
    client.post("/api/regions", json=REGION_DATA, headers=HEADERS)
    resp = client.post("/api/regions", json=REGION_DATA, headers=HEADERS)
    assert resp.status_code == 409


def test_list_regions(client):
    client.post("/api/regions", json=REGION_DATA, headers=HEADERS)
    client.post(
        "/api/regions",
        json={"name": "HCS华东-上海", "description": ""},
        headers=HEADERS,
    )
    resp = client.get("/api/regions?skip=0&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_list_regions_search(client):
    client.post("/api/regions", json=REGION_DATA, headers=HEADERS)
    client.post(
        "/api/regions",
        json={"name": "HCS华东-上海", "description": ""},
        headers=HEADERS,
    )
    resp = client.get("/api/regions?search=北京")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "HCS华北-北京"


def test_update_region(client):
    resp = client.post("/api/regions", json=REGION_DATA, headers=HEADERS)
    region_id = resp.json()["id"]

    resp = client.put(
        f"/api/regions/{region_id}",
        json={"name": "HCS华北-北京-UPDATED"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "HCS华北-北京-UPDATED"


def test_delete_region(client):
    resp = client.post("/api/regions", json=REGION_DATA, headers=HEADERS)
    region_id = resp.json()["id"]

    resp = client.delete(f"/api/regions/{region_id}", headers=HEADERS)
    assert resp.status_code == 204

    resp = client.get(f"/api/regions/{region_id}")
    assert resp.status_code == 404


def test_get_nonexistent_region(client):
    resp = client.get("/api/regions/nonexistent-id")
    assert resp.status_code == 404
