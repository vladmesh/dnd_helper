from http import HTTPStatus

from dnd_helper_api.db import engine
from sqlmodel import Session

from shared_models import CasterClass, Spell, SpellSchool


def test_list_spells_empty(client) -> None:
    response = client.get("/spells")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_spells_crud_lifecycle(client) -> None:
    # Create
    create_payload = {
        "school": "evocation",
        "classes": ["wizard"],
        "translations": {
            "ru": {"name": "Fire Bolt", "description": "A mote of fire"},
            "en": {"name": "Fire Bolt", "description": "A mote of fire"},
        },
    }
    created = client.post("/spells", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    spell_id = created.json()["id"]

    # Detail
    got = client.get(f"/spells/{spell_id}", params={"lang": "ru"})
    assert got.status_code == HTTPStatus.OK

    # Update
    update_payload = {
        "id": spell_id,
        "school": "conjuration",
        "classes": ["sorcerer"],
    }
    updated = client.put(f"/spells/{spell_id}", json=update_payload)
    assert updated.status_code == HTTPStatus.OK
    body = updated.json()
    assert body.get("classes") == ["sorcerer"]

    # Delete
    deleted = client.delete(f"/spells/{spell_id}")
    assert deleted.status_code == HTTPStatus.NO_CONTENT

    # Detail now 404
    missing = client.get(f"/spells/{spell_id}")
    assert missing.status_code == HTTPStatus.NOT_FOUND



def test_spells_accept_and_return_extended_fields(client) -> None:
    # Create with extended fields
    create_payload = {
        "school": "evocation",
        "level": 1,
        "ritual": False,
        "casting_time": "1 action",
        "range": "120 feet",
        "duration": "Instantaneous",
        "components": {"v": True, "s": True, "m": False, "material_desc": ""},
        "classes": ["wizard", "sorcerer"],
        "damage": {"dice": "1d10", "type": "fire"},
        "saving_throw": {"ability": "dexterity", "effect": "half on success"},
        "area": {"shape": "ray", "size": 0},
        "conditions": ["ignites objects"],
        "tags": ["damage", "cantrip-like"],
        "translations": {
            "ru": {"name": "Cinder Bolt", "description": "A mote of fire"},
        },
    }
    created = client.post("/spells", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    body = created.json()
    spell_id = body["id"]
    # Round-trip checks (stable fields)
    assert body["level"] == 1
    assert body["components"]["v"] is True
    assert set(body["classes"]) == {"wizard", "sorcerer"}
    assert body["damage"]["dice"] == "1d10"
    assert body["area"]["shape"] == "ray"

    # Labeled listing RU
    labeled_ru = client.get("/spells/labeled", params={"lang": "ru"})
    assert labeled_ru.status_code == HTTPStatus.OK
    items = labeled_ru.json()
    assert any(
        i["id"] == spell_id and i["school"]["label"] for i in items
    )

    # Labeled detail EN
    labeled_en = client.get(f"/spells/{spell_id}/labeled", params={"lang": "en"})
    assert labeled_en.status_code == HTTPStatus.OK
    body_en = labeled_en.json()
    assert isinstance(body_en["school"], dict) and {"code", "label"} <= set(body_en["school"].keys())


