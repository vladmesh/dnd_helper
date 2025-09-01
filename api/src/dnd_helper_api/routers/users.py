import logging
from typing import List

from dnd_helper_api.db import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from shared_models import User

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: User, session: Session = Depends(get_session)) -> User:  # noqa: B008
    # Ignore client-provided id
    user.id = None
    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info("User created", extra={"user_id": user.id})
    return user


@router.get("", response_model=List[User])
def list_users(session: Session = Depends(get_session)) -> List[User]:  # noqa: B008
    users = session.exec(select(User)).all()
    logger.info("Users listed", extra={"count": len(users)})
    return users


@router.get("/{user_id}", response_model=User)
def get_user(user_id: int, session: Session = Depends(get_session)) -> User:  # noqa: B008
    user = session.get(User, user_id)
    if user is None:
        logger.warning("User not found", extra={"user_id": user_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    logger.info("User fetched", extra={"user_id": user_id})
    return user


@router.put("/{user_id}", response_model=User)
def update_user(user_id: int, payload: User, session: Session = Depends(get_session)) -> User:  # noqa: B008
    user = session.get(User, user_id)
    if user is None:
        logger.warning("User not found for update", extra={"user_id": user_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.telegram_id = payload.telegram_id
    user.name = payload.name
    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info("User updated", extra={"user_id": user.id})
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, session: Session = Depends(get_session)) -> None:  # noqa: B008
    user = session.get(User, user_id)
    if user is None:
        logger.warning("User not found for delete", extra={"user_id": user_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    session.delete(user)
    session.commit()
    logger.info("User deleted", extra={"user_id": user_id})
    return None


