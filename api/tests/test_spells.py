from http import HTTPStatus

from sqlmodel import Session

from dnd_helper_api.db import engine
from shared_models import CasterClass, Spell, SpellSchool


def test_list_spells_empty(client) -> None:
    response = client.get("/spells")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_spells_crud_lifecycle(client) -> None:
    # Create
    create_payload = {
        "title": "Fire Bolt",
        "description": "A mote of fire",
        "caster_class": "wizard",
        "distance": 120,
        "school": "evocation",
    }
    created = client.post("/spells", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    spell_id = created.json()["id"]

    # Detail
    got = client.get(f"/spells/{spell_id}")
    assert got.status_code == HTTPStatus.OK
    assert got.json()["title"] == "Fire Bolt"

    # Update
    update_payload = {
        "id": spell_id,
        "title": "Cinder Bolt",
        "description": "A small ember",
        "caster_class": "sorcerer",
        "distance": 60,
        "school": "conjuration",
    }
    updated = client.put(f"/spells/{spell_id}", json=update_payload)
    assert updated.status_code == HTTPStatus.OK
    body = updated.json()
    assert body["title"] == "Cinder Bolt"
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
                title="Mage Hand",
                description="",
                caster_class=CasterClass.WIZARD,
                distance=30,
                school=SpellSchool.CONJURATION,
            )
        )
        session.add(
            Spell(
                title="Cure Wounds",
                description="",
                caster_class=CasterClass.CLERIC,
                distance=5,
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
    assert data[0]["title"] == "Mage Hand"


