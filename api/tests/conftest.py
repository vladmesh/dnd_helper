"""Common pytest fixtures for API tests.

All tests run against a real Postgres started by the test docker compose.
Alembic migrations are applied in the test container entrypoint before tests run.
"""

import os
from collections.abc import Iterator

# Enable admin endpoints for tests BEFORE importing app
os.environ.setdefault("ADMIN_ENABLED", "true")
os.environ.setdefault("ADMIN_TOKEN", "dev")

import pytest
from dnd_helper_api.db import engine
from dnd_helper_api.main import app
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlmodel import Session

from shared_models import Monster, Spell, User
from shared_models.monster_translation import MonsterTranslation
from shared_models.spell_translation import SpellTranslation


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_db() -> Iterator[None]:
    # Ensure a clean state before each test to avoid cross-test interference
    with Session(engine) as session:
        # Respect FKs: delete translation rows first, then base entities
        session.exec(delete(SpellTranslation))
        session.exec(delete(MonsterTranslation))
        session.exec(delete(Spell))
        session.exec(delete(Monster))
        session.exec(delete(User))
        session.commit()
    yield
    # No teardown needed; each test starts from a clean slate


