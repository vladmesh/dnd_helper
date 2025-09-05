from http import HTTPStatus


def test_create_monster_minimal_required_fields(client) -> None:
    payload = {"hp": 5, "ac": 12}
    resp = client.post("/monsters", json=payload)
    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    assert body["hp"] == 5 and body["ac"] == 12


def test_create_monster_ignores_extra_fields(client) -> None:
    payload = {"hp": 6, "ac": 11, "id": 999, "nonexistent": "x"}
    resp = client.post("/monsters", json=payload)
    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    assert body["id"] != 999
    assert "nonexistent" not in body


def test_create_monster_with_invalid_types_returns_422(client) -> None:
    payload = {"hp": "bad", "ac": 10}
    resp = client.post("/monsters", json=payload)
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_list_monsters_with_lang_and_pagination_params(client) -> None:
    # Prepare two items
    for _ in range(2):
        client.post("/monsters", json={"hp": 3, "ac": 10})
    # Lang param accepted; pagination params should not error even if ignored
    resp = client.get("/monsters", params={"lang": "ru", "limit": 1, "offset": 0})
    assert resp.status_code == HTTPStatus.OK
    assert isinstance(resp.json(), list)


def test_get_monster_detail_valid_and_404(client) -> None:
    created = client.post("/monsters", json={"hp": 8, "ac": 13})
    assert created.status_code == HTTPStatus.CREATED
    monster_id = created.json()["id"]

    got = client.get(f"/monsters/{monster_id}", params={"lang": "en"})
    assert got.status_code == HTTPStatus.OK

    missing = client.get("/monsters/9999999")
    assert missing.status_code == HTTPStatus.NOT_FOUND


def test_update_monster_with_partial_fields_and_bad_payloads(client) -> None:
    created = client.post("/monsters", json={"hp": 9, "ac": 14})
    monster_id = created.json()["id"]

    # Valid partial update
    upd = client.put(f"/monsters/{monster_id}", json={"id": monster_id, "hp": 7, "ac": 13, "type": "humanoid"})
    assert upd.status_code == HTTPStatus.OK
    body = upd.json()
    assert body["hp"] == 7 and body.get("type") == "humanoid"

    # Invalid type for field → 422
    bad = client.put(f"/monsters/{monster_id}", json={"id": monster_id, "hp": "bad", "ac": 13})
    assert bad.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_delete_monster_and_verify_404(client) -> None:
    created = client.post("/monsters", json={"hp": 4, "ac": 10})
    monster_id = created.json()["id"]

    deleted = client.delete(f"/monsters/{monster_id}")
    assert deleted.status_code == HTTPStatus.NO_CONTENT

    missing = client.get(f"/monsters/{monster_id}")
    assert missing.status_code == HTTPStatus.NOT_FOUND


