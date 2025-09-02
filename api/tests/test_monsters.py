from http import HTTPStatus

from dnd_helper_api.db import engine
from sqlmodel import Session

from shared_models import DangerLevel, Monster


def test_list_monsters_empty(client) -> None:
    response = client.get("/monsters")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_search_monsters_hit_and_miss(client) -> None:
    # Arrange: insert two monsters
    with Session(engine) as session:
        session.add(
            Monster(
                name="Goblin Scout",
                description="",
                cr=DangerLevel.CR_1_4,
                hp=7,
                ac=15,
            )
        )
        session.add(
            Monster(
                name="Orc Warrior",
                description="",
                cr=DangerLevel.CR_2,
                hp=15,
                ac=13,
            )
        )
        session.commit()

    # Act + Assert: miss
    miss = client.get("/monsters/search", params={"q": "dragon"})
    assert miss.status_code == HTTPStatus.OK
    assert miss.json() == []

    # Act + Assert: hit (case-insensitive partial)
    hit = client.get("/monsters/search", params={"q": "gob"})
    assert hit.status_code == HTTPStatus.OK
    data = hit.json()
    assert len(data) == 1
    assert data[0]["name"] == "Goblin Scout"


def test_monsters_accept_and_return_extended_fields(client) -> None:
    create_payload = {
        "name": "Gobbo",
        "description": "",
        "cr": "1/4",
        "hp": 7,
        "ac": 15,
        
        "type": "humanoid",
        "size": "Small",
        "alignment": "neutral evil",
        "speeds": {"walk": 30},
        # cr as enum-string
        "xp": 50,
        "proficiency_bonus": 2,
        "abilities": {"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8},
        "saving_throws": {"dex": 2},
        "skills": {"Stealth": 6},
        "senses": {"passive_perception": 9, "darkvision": 60},
        "languages": ["Common", "Goblin"],
        "traits": [{"name": "Nimble Escape", "desc": "bonus action disengage/hide"}],
        "actions": [{"name": "Scimitar", "desc": "+4 to hit"}],
        "reactions": [],
        "legendary_actions": [],
        "spellcasting": None,
        "tags": ["low-cr", "skirmisher"],
        "damage_immunities": [],
        "damage_resistances": [],
        "damage_vulnerabilities": [],
        "condition_immunities": [],
    }
    created = client.post("/monsters", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    body = created.json()
    monster_id = body["id"]
    assert body["name"] == "Gobbo"
    assert body["type"] == "humanoid"
    assert body["cr"] == "1/4"
    assert body["senses"]["darkvision"] == 60

    # Search by name
    found = client.get("/monsters/search", params={"q": "gobb"})
    assert found.status_code == HTTPStatus.OK
    assert any(m["id"] == monster_id for m in found.json())

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
        "name": "Troll",
        "description": "Regenerating giant",
        # no dangerous_lvl in Iteration 3
        "hp": 84,
        "ac": 15,
        
    }
    created = client.post("/monsters", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    created_body = created.json()
    monster_id = created_body["id"]
    assert isinstance(monster_id, int) and monster_id > 0

    # Detail
    got = client.get(f"/monsters/{monster_id}")
    assert got.status_code == HTTPStatus.OK
    assert got.json()["name"] == "Troll"

    # Update
    update_payload = {
        "id": monster_id,
        "name": "Young Troll",
        "description": "Regenerating giant (young)",
        "dangerous_lvl": "moderate",
        "hp": 68,
        "ac": 14,
        "speed": 30,
    }
    updated = client.put(f"/monsters/{monster_id}", json=update_payload)
    assert updated.status_code == HTTPStatus.OK
    assert updated.json()["name"] == "Young Troll"
    # dangerous_lvl removed; ensure name updated
    assert updated.json()["name"] == "Young Troll"

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
        "name": "Orc",
        "description": "Brutal warrior",
        # no dangerous_lvl in Iteration 3
        "hp": 15,
        "ac": 13,
        "speed": 30,
    }
    response = client.post("/monsters", json=payload)
    assert response.status_code == HTTPStatus.CREATED
    body = response.json()
    assert body["id"] != 999


