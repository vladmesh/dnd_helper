from http import HTTPStatus

from shared_models import User


def test_list_users_empty(client) -> None:
    response = client.get("/users")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_users_crud_lifecycle(client) -> None:
    # Create
    create_payload = {
        "telegram_id": 123456,
        "name": "Alice",
        "is_admin": False,
    }
    created = client.post("/users", json=create_payload)
    assert created.status_code == HTTPStatus.CREATED
    user_id = created.json()["id"]

    # Detail
    got = client.get(f"/users/{user_id}")
    assert got.status_code == HTTPStatus.OK
    assert got.json()["name"] == "Alice"

    # Update
    update_payload = {
        "id": user_id,
        "telegram_id": 654321,
        "name": "Alice Updated",
        "is_admin": True,
    }
    updated = client.put(f"/users/{user_id}", json=update_payload)
    assert updated.status_code == HTTPStatus.OK
    body = updated.json()
    assert body["telegram_id"] == 654321
    assert body["name"] == "Alice Updated"

    # Delete
    deleted = client.delete(f"/users/{user_id}")
    assert deleted.status_code == HTTPStatus.NO_CONTENT

    # Detail now 404
    missing = client.get(f"/users/{user_id}")
    assert missing.status_code == HTTPStatus.NOT_FOUND


