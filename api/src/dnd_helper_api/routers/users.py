from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from shared_models import User
from dnd_helper_api.db import get_session


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: User, session: Session = Depends(get_session)) -> User:
    # Ignore client-provided id
    user.id = None
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get("", response_model=List[User])
def list_users(session: Session = Depends(get_session)) -> List[User]:
    users = session.exec(select(User)).all()
    return users


@router.get("/{user_id}", response_model=User)
def get_user(user_id: int, session: Session = Depends(get_session)) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=User)
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


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, session: Session = Depends(get_session)) -> None:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    session.delete(user)
    session.commit()
    return None


