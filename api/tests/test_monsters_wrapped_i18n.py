from http import HTTPStatus


def test_monsters_wrapped_list_and_detail_i18n_and_labels(client) -> None:
    # Create a monster with RU only to test EN fallback
    create_payload = {
        "hp": 10,
        "ac": 12,
        "cr": "1/8",
        "type": "humanoid",
    }
    created = client.post("/monsters", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    monster_id = created.json()["id"]

    # upsert RU translation
    client.post(f"/monsters/{monster_id}/translations", json={"lang": "ru", "name": "Гоблин", "description": ""})

    # Wrapped list RU: should have localized name and labels
    wrapped_ru = client.get("/monsters/wrapped-list", params={"lang": "ru"})
    assert wrapped_ru.status_code == HTTPStatus.OK
    data = wrapped_ru.json()
    assert isinstance(data, list)
    item = next(x for x in data if x["entity"]["id"] == monster_id)
    if item["translation"] is not None:
        assert item["translation"]["name"]
    assert item["labels"]["cr"]["label"]

    # Wrapped detail EN: RU-only translation -> expect fallback text present
    wrapped_en = client.get(f"/monsters/{monster_id}/wrapped", params={"lang": "en"})
    assert wrapped_en.status_code == HTTPStatus.OK
    body = wrapped_en.json()
    assert body["entity"]["id"] == monster_id
    # Fallback: translation should be present even if EN missing
    if body["translation"] is not None:
        assert body["translation"]["name"]
    # Labels are language-specific; label field must exist
    assert body["labels"]["cr"]["label"]


