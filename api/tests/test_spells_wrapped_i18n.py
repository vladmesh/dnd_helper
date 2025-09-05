from http import HTTPStatus


def test_spells_wrapped_list_and_detail_i18n_and_labels(client) -> None:
    # Create a spell with EN only to test RU fallback
    create_payload = {
        "school": "evocation",
        "classes": ["wizard"],
        "translations": {
            "en": {"name": "Spark", "description": "Tiny spark of fire"},
        },
    }
    created = client.post("/spells", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    spell_id = created.json()["id"]

    # Wrapped list EN: should have localized name and labels
    wrapped_en = client.get("/spells/list/wrapped", params={"lang": "en"})
    assert wrapped_en.status_code == HTTPStatus.OK
    data = wrapped_en.json()
    assert isinstance(data, list)
    item = next(x for x in data if x["entity"]["id"] == spell_id)
    assert item["translation"]["name"]
    assert item["labels"]["school"]["label"]

    # Wrapped detail RU: EN-only translation -> expect fallback text present
    wrapped_ru = client.get(f"/spells/{spell_id}/wrapped", params={"lang": "ru"})
    assert wrapped_ru.status_code == HTTPStatus.OK
    body = wrapped_ru.json()
    assert body["entity"]["id"] == spell_id
    assert body["translation"]["name"]
    # Labels: school/classes are labeled dicts
    assert body["labels"]["school"]["label"]
    assert isinstance(body["labels"].get("classes"), list)


