import logging
from typing import List, Optional

from dnd_helper_api.db import get_session
from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlmodel import Session, select

from shared_models import User
from shared_models.enums import Language

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
def list_users(  # noqa: B008
    session: Session = Depends(get_session),
    telegram_id: Optional[int] = None,
) -> List[User]:
    stmt = select(User)
    if telegram_id is not None:
        stmt = stmt.where(User.telegram_id == telegram_id)
    users = session.exec(stmt).all()
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


@router.get("/by-telegram/{telegram_id}", response_model=User)
def get_user_by_telegram(telegram_id: int, session: Session = Depends(get_session)) -> User:  # noqa: B008
    user = session.exec(select(User).where(User.telegram_id == telegram_id)).first()
    if user is None:
        logger.warning("User not found by telegram", extra={"telegram_id": telegram_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    logger.info("User fetched by telegram", extra={"user_id": user.id, "telegram_id": telegram_id})
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


@router.patch("/{user_id}", response_model=User)
def patch_user(
    user_id: int,
    lang: Language = Body(..., embed=True),
    session: Session = Depends(get_session),  # noqa: B008
) -> User:
    """Minimal partial update: currently supports updating language only.
    
    Expects body like: {"lang": "ru" | "en"}
    """
    user = session.get(User, user_id)
    if user is None:
        logger.warning("User not found for patch", extra={"user_id": user_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.lang = lang
    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info("User language updated", extra={"user_id": user.id, "lang": user.lang})
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


