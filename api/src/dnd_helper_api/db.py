import os
from sqlmodel import Session, SQLModel, create_engine


def _build_database_url() -> str:
    db_user = os.environ["POSTGRES_USER"]
    db_password = os.environ["POSTGRES_PASSWORD"]
    db_name = os.environ["POSTGRES_DB"]
    db_host = os.environ["POSTGRES_HOST"]
    db_port = os.environ["POSTGRES_PORT"]

    return f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


DATABASE_URL = _build_database_url()
engine = create_engine(DATABASE_URL, echo=False)


def get_session() -> Session:
    with Session(engine) as session:
        yield session


