import os
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from sqlmodel import Session, SQLModel, create_engine, select

from shared_models import User


app = FastAPI(title="DnD Helper API")


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


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


@app.on_event("startup")
def on_startup() -> None:
    # Ensure all SQLModel tables are created
    SQLModel.metadata.create_all(engine)


@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: User, session: Session = Depends(get_session)) -> User:
    # Ignore client-provided id
    user.id = None
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.get("/users", response_model=List[User])
def list_users(session: Session = Depends(get_session)) -> List[User]:
    users = session.exec(select(User)).all()
    return users


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int, session: Session = Depends(get_session)) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=User)
def update_user(user_id: int, payload: User, session: Session = Depends(get_session)) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.telegram_id = payload.telegram_id
    user.name = payload.name
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, session: Session = Depends(get_session)) -> None:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    session.delete(user)
    session.commit()
    return None

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dnd_helper_api.main:app", host="0.0.0.0", port=8000)
