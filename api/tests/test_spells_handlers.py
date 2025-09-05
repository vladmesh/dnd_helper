from http import HTTPStatus


def test_create_spell_minimal_required_fields(client) -> None:
    payload = {"school": "evocation"}
    resp = client.post("/spells", json=payload)
    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    assert body["school"] == "evocation"


def test_create_spell_rejects_extra_fields(client) -> None:
    payload = {"school": "conjuration", "nonexistent": "x"}
    resp = client.post("/spells", json=payload)
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_create_spell_invalid_school_422(client) -> None:
    payload = {"school": "invalid_school"}
    resp = client.post("/spells", json=payload)
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_list_spells_with_lang_and_pagination_params(client) -> None:
    for _ in range(2):
        client.post("/spells", json={"school": "evocation"})
    resp = client.get("/spells", params={"lang": "en", "limit": 1, "offset": 0})
    assert resp.status_code == HTTPStatus.OK
    assert isinstance(resp.json(), list)


def test_get_spell_detail_valid_and_404(client) -> None:
    created = client.post("/spells", json={"school": "evocation"})
    spell_id = created.json()["id"]

    got = client.get(f"/spells/{spell_id}", params={"lang": "ru"})
    assert got.status_code == HTTPStatus.OK

    missing = client.get("/spells/9999999")
    assert missing.status_code == HTTPStatus.NOT_FOUND


def test_update_spell_partial(client) -> None:
    created = client.post("/spells", json={"school": "evocation"})
    spell_id = created.json()["id"]

    upd = client.put(
        f"/spells/{spell_id}",
        json={
            "id": spell_id,
            "school": "evocation",
            "level": 2,
            "classes": ["wizard", "sorcerer"],
            "duration": "Instantaneous",
        },
    )
    assert upd.status_code == HTTPStatus.OK
    data = upd.json()
    assert data["level"] == 2
    assert data["school"] == "evocation"
    assert set(data.get("classes") or []) == {"wizard", "sorcerer"}


def test_delete_spell_and_verify_404(client) -> None:
    created = client.post("/spells", json={"school": "conjuration"})
    spell_id = created.json()["id"]

    deleted = client.delete(f"/spells/{spell_id}")
    assert deleted.status_code == HTTPStatus.NO_CONTENT

    missing = client.get(f"/spells/{spell_id}")
    assert missing.status_code == HTTPStatus.NOT_FOUND


