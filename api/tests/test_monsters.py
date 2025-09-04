from http import HTTPStatus

from dnd_helper_api.db import engine
from sqlmodel import Session

from shared_models import DangerLevel, Monster


def test_list_monsters_empty(client) -> None:
    response = client.get("/monsters")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_monsters_create_and_list_with_translations(client) -> None:
    create_payload = {
        "hp": 7,
        "ac": 15,
        "cr": "1/4",
        "type": "humanoid",
        "senses": {"passive_perception": 9},
        "translations": {
            "ru": {"name": "Gobbo", "description": ""},
            "en": {"name": "Gobbo", "description": ""},
        },
    }
    created = client.post("/monsters", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    monster_id = created.json()["id"]
    assert isinstance(monster_id, int) and monster_id > 0

    # List and ensure monster is present
    listed = client.get("/monsters", params={"lang": "ru"})
    assert listed.status_code == HTTPStatus.OK
    assert any(m["id"] == monster_id for m in listed.json())



def test_monsters_accept_and_return_extended_fields(client) -> None:
    create_payload = {
        "cr": "1/4",
        "hp": 7,
        "ac": 15,
        "type": "humanoid",
        "size": "Small",
        "alignment": "neutral evil",
        "xp": 50,
        "proficiency_bonus": 2,
        "abilities": {"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8},
        "saving_throws": {"dex": 2},
        "skills": {"Stealth": 6},
        "senses": {"passive_perception": 9, "darkvision": 60},
        "languages": ["Common", "Goblin"],
        "tags": ["low-cr", "skirmisher"],
        "damage_immunities": [],
        "damage_resistances": [],
        "damage_vulnerabilities": [],
        "condition_immunities": [],
        "translations": {
            "ru": {
                "name": "Gobbo",
                "description": "",
                "traits": [{"name": "Nimble Escape", "text": "bonus action disengage/hide"}],
                "actions": [{"name": "Scimitar", "text": "+4 to hit"}],
                "reactions": [],
                "legendary_actions": [],
                "spellcasting": None,
            }
        },
    }
    created = client.post("/monsters", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    body = created.json()
    monster_id = body["id"]
    assert body["type"] == "humanoid"
    assert body["cr"] == "1/4"
    assert body["senses"]["darkvision"] == 60

    # Labeled listing RU
    labeled_ru = client.get("/monsters/labeled", params={"lang": "ru"})
    assert labeled_ru.status_code == HTTPStatus.OK
    items = labeled_ru.json()
    assert any(i["id"] == monster_id and isinstance(i.get("cr"), dict) for i in items)

    # Labeled detail EN
    labeled_en = client.get(f"/monsters/{monster_id}/labeled", params={"lang": "en"})
    assert labeled_en.status_code == HTTPStatus.OK
    body_en = labeled_en.json()
    assert isinstance(body_en.get("cr"), dict) and {"code", "label"} <= set(body_en["cr"].keys())



def test_monster_crud_lifecycle(client) -> None:
    # Create
    create_payload = {
        "hp": 84,
        "ac": 15,
        "translations": {"ru": {"name": "Troll", "description": "Regenerating giant"}},
    }
    created = client.post("/monsters", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    created_body = created.json()
    monster_id = created_body["id"]
    assert isinstance(monster_id, int) and monster_id > 0

    # Detail
    got = client.get(f"/monsters/{monster_id}", params={"lang": "ru"})
    assert got.status_code == HTTPStatus.OK

    # Update base and translations
    update_payload = {
        "id": monster_id,
        "hp": 68,
        "ac": 14,
    }
    updated = client.put(f"/monsters/{monster_id}", json=update_payload)
    assert updated.status_code == HTTPStatus.OK

    # List should include exactly one
    listed = client.get("/monsters")
    assert listed.status_code == HTTPStatus.OK
    assert any(m["id"] == monster_id for m in listed.json())

    # Delete
    deleted = client.delete(f"/monsters/{monster_id}")
    assert deleted.status_code == HTTPStatus.NO_CONTENT

    # Detail now 404
    missing = client.get(f"/monsters/{monster_id}")
    assert missing.status_code == HTTPStatus.NOT_FOUND



def test_monster_create_ignores_client_id(client) -> None:
    # Client provides an explicit id, but API should ignore it
    payload = {
        "id": 999,
        "hp": 15,
        "ac": 13,
    }
    response = client.post("/monsters", json=payload)
    assert response.status_code == HTTPStatus.CREATED
    body = response.json()
    assert body["id"] != 999


