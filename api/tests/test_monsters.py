from http import HTTPStatus

from sqlmodel import Session

from dnd_helper_api.db import engine
from shared_models import Monster, DangerLevel


def test_list_monsters_empty(client) -> None:
    response = client.get("/monsters")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_search_monsters_hit_and_miss(client) -> None:
    # Arrange: insert two monsters
    with Session(engine) as session:
        session.add(
            Monster(
                title="Goblin Scout",
                description="",
                dangerous_lvl=DangerLevel.LOW,
                hp=7,
                ac=15,
                speed=30,
            )
        )
        session.add(
            Monster(
                title="Orc Warrior",
                description="",
                dangerous_lvl=DangerLevel.MODERATE,
                hp=15,
                ac=13,
                speed=30,
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
    assert data[0]["title"] == "Goblin Scout"


