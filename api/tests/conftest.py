"""Common pytest fixtures for API tests.

All tests run against a real Postgres started by the test docker compose.
Alembic migrations are applied in the test container entrypoint before tests run.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlmodel import Session

from dnd_helper_api.db import engine
from dnd_helper_api.main import app
from shared_models import Monster, Spell, User


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_db() -> Iterator[None]:
    # Ensure a clean state before each test to avoid cross-test interference
    with Session(engine) as session:
        # Order matters only if there are FKs; current models are independent
        session.exec(delete(Spell))
        session.exec(delete(Monster))
        session.exec(delete(User))
        session.commit()
    yield
    # No teardown needed; each test starts from a clean slate


