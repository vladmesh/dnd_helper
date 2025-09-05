from http import HTTPStatus


def test_create_monster_minimal_required_fields(client) -> None:
    payload = {"hp": 5, "ac": 12}
    resp = client.post("/monsters", json=payload)
    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    assert body["hp"] == 5 and body["ac"] == 12


def test_create_monster_rejects_extra_fields(client) -> None:
    payload = {"hp": 6, "ac": 11, "nonexistent": "x"}
    resp = client.post("/monsters", json=payload)
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_create_monster_with_minimal_valid_data(client) -> None:
    payload = {"hp": 10, "ac": 12}
    resp = client.post("/monsters", json=payload)
    assert resp.status_code == HTTPStatus.CREATED
    data = resp.json()
    assert data["hp"] == 10
    assert data["ac"] == 12


def test_list_monsters_with_lang_and_pagination_params(client) -> None:
    # Prepare two items
    for _ in range(2):
        client.post("/monsters", json={"hp": 3, "ac": 10})
    # Lang param accepted; pagination params should not error even if ignored
    resp = client.get("/monsters/list/raw", params={"lang": "ru", "limit": 1, "offset": 0})
    assert resp.status_code == HTTPStatus.OK
    assert isinstance(resp.json(), list)


def test_list_monsters_list_aliases(client) -> None:
    # Prepare two items
    for _ in range(2):
        client.post("/monsters", json={"hp": 3, "ac": 10})
    # /list/raw alias
    raw = client.get("/monsters/list/raw", params={"lang": "ru"})
    assert raw.status_code == HTTPStatus.OK
    assert isinstance(raw.json(), list)
    # /list/wrapped alias
    wrapped = client.get("/monsters/list/wrapped", params={"lang": "en"})
    assert wrapped.status_code == HTTPStatus.OK
    data = wrapped.json()
    assert isinstance(data, list)


def test_monsters_legacy_list_has_deprecation_headers(client) -> None:
    # Prepare one item
    client.post("/monsters", json={"hp": 3, "ac": 10})
    resp_raw = client.get("/monsters/list/raw", params={"lang": "en"})
    assert resp_raw.status_code == HTTPStatus.OK
    # new canonical path should not carry deprecation headers
    assert resp_raw.headers.get("Deprecation") in (None, "")

    resp_wrapped = client.get("/monsters/list/wrapped", params={"lang": "en"})
    assert resp_wrapped.status_code == HTTPStatus.OK
    assert resp_wrapped.headers.get("Deprecation") in (None, "")


def test_get_monster_detail_valid_and_404(client) -> None:
    created = client.post("/monsters", json={"hp": 8, "ac": 13})
    assert created.status_code == HTTPStatus.CREATED
    monster_id = created.json()["id"]

    got = client.get(f"/monsters/{monster_id}", params={"lang": "en"})
    assert got.status_code == HTTPStatus.OK

    missing = client.get("/monsters/9999999")
    assert missing.status_code == HTTPStatus.NOT_FOUND


def test_update_monster_with_partial_fields(client) -> None:
    created = client.post("/monsters", json={"hp": 9, "ac": 14})
    monster_id = created.json()["id"]

    # Valid partial update
    upd = client.put(f"/monsters/{monster_id}", json={"id": monster_id, "hp": 7, "ac": 13, "type": "humanoid"})
    assert upd.status_code == HTTPStatus.OK
    body = upd.json()
    assert body["hp"] == 7 and body.get("type") == "humanoid"


def test_delete_monster_and_verify_404(client) -> None:
    created = client.post("/monsters", json={"hp": 4, "ac": 10})
    monster_id = created.json()["id"]

    deleted = client.delete(f"/monsters/{monster_id}")
    assert deleted.status_code == HTTPStatus.NO_CONTENT

    missing = client.get(f"/monsters/{monster_id}")
    assert missing.status_code == HTTPStatus.NOT_FOUND


