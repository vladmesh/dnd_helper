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
        "name": "Fire Bolt",
        "description": "A mote of fire",
        "caster_class": "wizard",
        
        "school": "evocation",
    }
    created = client.post("/spells", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    spell_id = created.json()["id"]

    # Detail
    got = client.get(f"/spells/{spell_id}")
    assert got.status_code == HTTPStatus.OK
    assert got.json()["name"] == "Fire Bolt"

    # Update
    update_payload = {
        "id": spell_id,
        "name": "Cinder Bolt",
        "description": "A small ember",
        "caster_class": "sorcerer",
        
        "school": "conjuration",
    }
    updated = client.put(f"/spells/{spell_id}", json=update_payload)
    assert updated.status_code == HTTPStatus.OK
    body = updated.json()
    assert body["name"] == "Cinder Bolt"
    assert body["caster_class"] == "sorcerer"

    # Delete
    deleted = client.delete(f"/spells/{spell_id}")
    assert deleted.status_code == HTTPStatus.NO_CONTENT

    # Detail now 404
    missing = client.get(f"/spells/{spell_id}")
    assert missing.status_code == HTTPStatus.NOT_FOUND


def test_spells_search_hit_and_miss(client) -> None:
    # Arrange
    with Session(engine) as session:
        session.add(
            Spell(
                name="Mage Hand",
                description="",
                caster_class=CasterClass.WIZARD,
                
                school=SpellSchool.CONJURATION,
            )
        )
        session.add(
            Spell(
                name="Cure Wounds",
                description="",
                caster_class=CasterClass.CLERIC,
                
                school=SpellSchool.EVOCATION,
            )
        )
        session.commit()

    miss = client.get("/spells/search", params={"q": "fireball"})
    assert miss.status_code == HTTPStatus.OK
    assert miss.json() == []

    hit = client.get("/spells/search", params={"q": "mage"})
    assert hit.status_code == HTTPStatus.OK
    data = hit.json()
    assert len(data) == 1
    assert data[0]["name"] == "Mage Hand"


def test_spells_accept_and_return_extended_fields(client) -> None:
    # Create with extended fields
    create_payload = {
        "name": "Cinder Bolt",
        "description": "A mote of fire",
        "caster_class": "wizard",
        "distance": 120,
        "school": "evocation",
        "level": 1,
        "ritual": False,
        "casting_time": "1 action",
        "range": "120 feet",
        "duration": "Instantaneous",
        "concentration": False,
        "components": {"v": True, "s": True, "m": False, "material_desc": ""},
        "classes": ["wizard", "sorcerer"],
        "damage": {"dice": "1d10", "type": "fire"},
        "saving_throw": {"ability": "dexterity", "effect": "half on success"},
        "area": {"shape": "ray", "size": 0},
        "conditions": ["ignites objects"],
        "tags": ["damage", "cantrip-like"],
    }
    created = client.post("/spells", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    body = created.json()
    spell_id = body["id"]
    # Round-trip checks
    assert body["name"] == "Cinder Bolt"
    assert body["level"] == 1
    assert body["components"]["v"] is True
    assert set(body["classes"]) == {"wizard", "sorcerer"}
    assert body["damage"]["dice"] == "1d10"
    assert body["area"]["shape"] == "ray"
    # Search by name
    found = client.get("/spells/search", params={"q": "cinder"})
    assert found.status_code == HTTPStatus.OK
    assert any(s["id"] == spell_id for s in found.json())


