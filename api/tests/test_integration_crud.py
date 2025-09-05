"""Integration tests for complete CRUD lifecycles (raw and wrapped endpoints)."""

from http import HTTPStatus


def test_monsters_crud_lifecycle_raw_endpoints(client) -> None:
    """Test complete CRUD lifecycle for monsters via raw endpoints."""
    # CREATE
    create_payload = {
        "hp": 15,
        "ac": 14,
        "cr": "1/2",
        "type": "humanoid",
        "size": "medium",
    }
    created = client.post("/monsters", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    monster_data = created.json()
    monster_id = monster_data["id"]
    # upsert translations separately
    resp_tr_en = client.post(f"/monsters/{monster_id}/translations", json={"lang": "en", "name": "Orc Warrior", "description": "A fierce orc fighter"})
    assert resp_tr_en.status_code == HTTPStatus.NO_CONTENT
    resp_tr_ru = client.post(f"/monsters/{monster_id}/translations", json={"lang": "ru", "name": "Орк-воин", "description": "Свирепый орк-воитель"})
    assert resp_tr_ru.status_code == HTTPStatus.NO_CONTENT
    assert monster_data["hp"] == 15
    assert monster_data["ac"] == 14

    # READ (GET)
    retrieved = client.get(f"/monsters/{monster_id}")
    assert retrieved.status_code == HTTPStatus.OK
    retrieved_data = retrieved.json()
    assert retrieved_data["id"] == monster_id
    assert retrieved_data["hp"] == 15

    # UPDATE (PUT)
    update_payload = {
        "id": monster_id,
        "hp": 20,
        "ac": 16,
        "cr": "1",
        "type": "humanoid",
        "size": "medium"
    }
    updated = client.put(f"/monsters/{monster_id}", json=update_payload)
    assert updated.status_code == HTTPStatus.OK
    updated_data = updated.json()
    assert updated_data["hp"] == 20
    assert updated_data["ac"] == 16
    assert updated_data["cr"] == "1"

    # READ again to verify update
    retrieved_after_update = client.get(f"/monsters/{monster_id}")
    assert retrieved_after_update.status_code == HTTPStatus.OK
    final_data = retrieved_after_update.json()
    assert final_data["hp"] == 20
    assert final_data["ac"] == 16

    # DELETE
    deleted = client.delete(f"/monsters/{monster_id}")
    assert deleted.status_code == HTTPStatus.NO_CONTENT

    # VERIFY 404 after deletion
    not_found = client.get(f"/monsters/{monster_id}")
    assert not_found.status_code == HTTPStatus.NOT_FOUND


def test_monsters_crud_lifecycle_wrapped_endpoints(client) -> None:
    """Test complete CRUD lifecycle for monsters via wrapped endpoints."""
    # CREATE
    create_payload = {
        "hp": 12,
        "ac": 13,
        "cr": "1/4",
        "type": "beast",
        "size": "small",
    }
    created = client.post("/monsters", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    monster_id = created.json()["id"]

    # upsert translations
    client.post(f"/monsters/{monster_id}/translations", json={"lang": "en", "name": "Giant Rat", "description": "A large rodent"})
    client.post(f"/monsters/{monster_id}/translations", json={"lang": "ru", "name": "Гигантская крыса", "description": "Большой грызун"})

    # READ wrapped (EN)
    retrieved_wrapped_en = client.get(f"/monsters/{monster_id}/wrapped", params={"lang": "en"})
    assert retrieved_wrapped_en.status_code == HTTPStatus.OK
    wrapped_data_en = retrieved_wrapped_en.json()
    assert wrapped_data_en["entity"]["id"] == monster_id
    assert "translation" in wrapped_data_en
    assert "labels" in wrapped_data_en
    assert wrapped_data_en["translation"]["name"] == "Giant Rat"
    assert wrapped_data_en["labels"]["type"]["code"] == "beast"
    assert "label" in wrapped_data_en["labels"]["type"]

    # READ wrapped (RU)
    retrieved_wrapped_ru = client.get(f"/monsters/{monster_id}/wrapped", params={"lang": "ru"})
    assert retrieved_wrapped_ru.status_code == HTTPStatus.OK
    wrapped_data_ru = retrieved_wrapped_ru.json()
    assert wrapped_data_ru["translation"]["name"] == "Гигантская крыса"

    # UPDATE via raw endpoint
    update_payload = {
        "id": monster_id,
        "hp": 18,
        "ac": 13,
        "cr": "1/8",
        "type": "beast",
        "size": "small"
    }
    updated = client.put(f"/monsters/{monster_id}", json=update_payload)
    assert updated.status_code == HTTPStatus.OK

    # READ wrapped again to verify update
    retrieved_after_update = client.get(f"/monsters/{monster_id}/wrapped", params={"lang": "en"})
    assert retrieved_after_update.status_code == HTTPStatus.OK
    updated_wrapped_data = retrieved_after_update.json()
    assert updated_wrapped_data["entity"]["hp"] == 18
    assert updated_wrapped_data["entity"]["ac"] == 13

    # DELETE
    deleted = client.delete(f"/monsters/{monster_id}")
    assert deleted.status_code == HTTPStatus.NO_CONTENT

    # VERIFY 404 after deletion for wrapped endpoint
    not_found_wrapped = client.get(f"/monsters/{monster_id}/wrapped", params={"lang": "en"})
    assert not_found_wrapped.status_code == HTTPStatus.NOT_FOUND


def test_spells_crud_lifecycle_raw_endpoints(client) -> None:
    """Test complete CRUD lifecycle for spells via raw endpoints."""
    # CREATE
    create_payload = {
        "school": "evocation",
        "level": 1,
        "classes": ["wizard", "sorcerer"],
        "casting_time": "1 action",
        "range": "60 feet",
        "duration": "Instantaneous",
    }
    created = client.post("/spells", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    spell_data = created.json()
    spell_id = spell_data["id"]
    # upsert translations
    client.post(f"/spells/{spell_id}/translations", json={"lang": "en", "name": "Fire Bolt", "description": "Throw a bolt of fire"})
    client.post(f"/spells/{spell_id}/translations", json={"lang": "ru", "name": "Огненный снаряд", "description": "Бросить снаряд огня"})
    assert spell_data["school"] == "evocation"
    assert spell_data["level"] == 1
    assert set(spell_data["classes"]) == {"wizard", "sorcerer"}

    # READ (GET)
    retrieved = client.get(f"/spells/{spell_id}")
    assert retrieved.status_code == HTTPStatus.OK
    retrieved_data = retrieved.json()
    assert retrieved_data["id"] == spell_id
    assert retrieved_data["school"] == "evocation"

    # UPDATE (PUT)
    update_payload = {
        "id": spell_id,
        "school": "evocation",
        "level": 2,
        "range": "120 feet",
        "duration": "1 minute",
        "classes": ["wizard", "sorcerer"],
        "casting_time": "1 action"
    }
    updated = client.put(f"/spells/{spell_id}", json=update_payload)
    assert updated.status_code == HTTPStatus.OK
    updated_data = updated.json()
    assert updated_data["level"] == 2
    assert updated_data["range"] == "120 feet"

    # READ again to verify update
    retrieved_after_update = client.get(f"/spells/{spell_id}")
    assert retrieved_after_update.status_code == HTTPStatus.OK
    final_data = retrieved_after_update.json()
    assert final_data["level"] == 2
    assert final_data["range"] == "120 feet"

    # DELETE
    deleted = client.delete(f"/spells/{spell_id}")
    assert deleted.status_code == HTTPStatus.NO_CONTENT

    # VERIFY 404 after deletion
    not_found = client.get(f"/spells/{spell_id}")
    assert not_found.status_code == HTTPStatus.NOT_FOUND


def test_spells_crud_lifecycle_wrapped_endpoints(client) -> None:
    """Test complete CRUD lifecycle for spells via wrapped endpoints."""
    # CREATE
    create_payload = {
        "school": "conjuration",
        "level": 0,
        "classes": ["wizard"],
        "casting_time": "1 action",
        "range": "10 feet",
        "duration": "1 minute",
    }
    created = client.post("/spells", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    spell_id = created.json()["id"]

    # upsert translations
    client.post(f"/spells/{spell_id}/translations", json={"lang": "en", "name": "Prestidigitation", "description": "Minor magical effects"})
    client.post(f"/spells/{spell_id}/translations", json={"lang": "ru", "name": "Фокусы", "description": "Малые магические эффекты"})

    # READ wrapped (EN)
    retrieved_wrapped_en = client.get(f"/spells/{spell_id}/wrapped", params={"lang": "en"})
    assert retrieved_wrapped_en.status_code == HTTPStatus.OK
    wrapped_data_en = retrieved_wrapped_en.json()
    assert wrapped_data_en["entity"]["id"] == spell_id
    assert "translation" in wrapped_data_en
    assert "labels" in wrapped_data_en
    assert wrapped_data_en["translation"]["name"] == "Prestidigitation"
    assert wrapped_data_en["labels"]["school"]["code"] == "conjuration"
    assert "label" in wrapped_data_en["labels"]["school"]
    assert isinstance(wrapped_data_en["labels"]["classes"], list)

    # READ wrapped (RU)
    retrieved_wrapped_ru = client.get(f"/spells/{spell_id}/wrapped", params={"lang": "ru"})
    assert retrieved_wrapped_ru.status_code == HTTPStatus.OK
    wrapped_data_ru = retrieved_wrapped_ru.json()
    assert wrapped_data_ru["translation"]["name"] == "Фокусы"

    # UPDATE via raw endpoint
    update_payload = {
        "id": spell_id,
        "school": "conjuration",
        "level": 1,
        "range": "30 feet",
        "classes": ["wizard"],
        "casting_time": "1 action",
        "duration": "1 minute"
    }
    updated = client.put(f"/spells/{spell_id}", json=update_payload)
    assert updated.status_code == HTTPStatus.OK

    # READ wrapped again to verify update
    retrieved_after_update = client.get(f"/spells/{spell_id}/wrapped", params={"lang": "en"})
    assert retrieved_after_update.status_code == HTTPStatus.OK
    updated_wrapped_data = retrieved_after_update.json()
    assert updated_wrapped_data["entity"]["level"] == 1
    assert updated_wrapped_data["entity"]["range"] == "30 feet"

    # DELETE
    deleted = client.delete(f"/spells/{spell_id}")
    assert deleted.status_code == HTTPStatus.NO_CONTENT

    # VERIFY 404 after deletion for wrapped endpoint
    not_found_wrapped = client.get(f"/spells/{spell_id}/wrapped", params={"lang": "en"})
    assert not_found_wrapped.status_code == HTTPStatus.NOT_FOUND


def test_monsters_wrapped_list_integration(client) -> None:
    """Test wrapped list endpoint with multiple monsters and i18n."""
    # Create multiple monsters with different translations
    monsters_data = [
        {
            "hp": 10,
            "ac": 12,
            "cr": "1/8",
            "type": "humanoid",
        },
        {
            "hp": 20,
            "ac": 15,
            "cr": "1",
            "type": "beast",
        }
    ]

    created_ids = []
    for monster in monsters_data:
        created = client.post("/monsters", json=monster)
        assert created.status_code == HTTPStatus.CREATED
        created_ids.append(created.json()["id"])

    # add translations
    client.post(f"/monsters/{created_ids[0]}/translations", json={"lang": "ru", "name": "Гоблин", "description": ""})
    client.post(f"/monsters/{created_ids[1]}/translations", json={"lang": "en", "name": "Wolf", "description": "A wild wolf"})

    # Test wrapped list EN (should have fallbacks)
    wrapped_list_en = client.get("/monsters/wrapped-list", params={"lang": "en"})
    assert wrapped_list_en.status_code == HTTPStatus.OK
    data_en = wrapped_list_en.json()
    assert isinstance(data_en, list)
    assert len(data_en) >= 2

    # Verify structure and fallbacks
    for item in data_en:
        assert "entity" in item
        assert "translation" in item
        assert "labels" in item
        # Translation should always have name (fallback or actual)
        if item["translation"] is not None:
            assert "name" in item["translation"]
        # Labels should have proper structure
        if item["entity"].get("type"):
            assert "type" in item["labels"]
            assert "code" in item["labels"]["type"]
            assert "label" in item["labels"]["type"]

    # Test wrapped list RU (should have fallbacks)
    wrapped_list_ru = client.get("/monsters/wrapped-list", params={"lang": "ru"})
    assert wrapped_list_ru.status_code == HTTPStatus.OK
    data_ru = wrapped_list_ru.json()
    assert len(data_ru) >= 2

    # Clean up
    for monster_id in created_ids:
        client.delete(f"/monsters/{monster_id}")


def test_spells_wrapped_list_integration(client) -> None:
    """Test wrapped list endpoint with multiple spells and i18n."""
    # Create multiple spells with different translations
    spells_data = [
        {
            "school": "evocation",
            "classes": ["wizard"],
        },
        {
            "school": "conjuration",
            "classes": ["cleric"],
        }
    ]

    created_ids = []
    for spell in spells_data:
        created = client.post("/spells", json=spell)
        assert created.status_code == HTTPStatus.CREATED
        created_ids.append(created.json()["id"])

    # add translations
    client.post(f"/spells/{created_ids[0]}/translations", json={"lang": "en", "name": "Fire Bolt", "description": "Throw fire"})
    client.post(f"/spells/{created_ids[1]}/translations", json={"lang": "ru", "name": "Лечение ран", "description": "Исцеление"})

    # Test wrapped list EN
    wrapped_list_en = client.get("/spells/wrapped-list", params={"lang": "en"})
    assert wrapped_list_en.status_code == HTTPStatus.OK
    data_en = wrapped_list_en.json()
    assert isinstance(data_en, list)
    assert len(data_en) >= 2

    # Verify structure
    for item in data_en:
        assert "entity" in item
        assert "translation" in item
        assert "labels" in item
        assert "name" in item["translation"]
        if item["entity"].get("school"):
            assert "school" in item["labels"]
            assert "code" in item["labels"]["school"]
            assert "label" in item["labels"]["school"]

    # Test wrapped list RU
    wrapped_list_ru = client.get("/spells/wrapped-list", params={"lang": "ru"})
    assert wrapped_list_ru.status_code == HTTPStatus.OK
    data_ru = wrapped_list_ru.json()
    assert len(data_ru) >= 2

    # Clean up
    for spell_id in created_ids:
        client.delete(f"/spells/{spell_id}")
