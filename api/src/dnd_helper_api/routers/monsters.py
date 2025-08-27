from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from shared_models import Monster
from dnd_helper_api.db import get_session


router = APIRouter(prefix="/monsters", tags=["monsters"])


@router.get("/search", response_model=List[Monster])
def search_monsters(q: str, session: Session = Depends(get_session)) -> List[Monster]:
    if not q:
        return []
    monsters = session.exec(
        select(Monster).where(Monster.title.ilike(f"%{q}%"))
    ).all()
    return monsters


@router.post("", response_model=Monster, status_code=status.HTTP_201_CREATED)
def create_monster(monster: Monster, session: Session = Depends(get_session)) -> Monster:
    # Ignore client-provided id
    monster.id = None
    session.add(monster)
    session.commit()
    session.refresh(monster)
    return monster


@router.get("", response_model=List[Monster])
def list_monsters(session: Session = Depends(get_session)) -> List[Monster]:
    monsters = session.exec(select(Monster)).all()
    return monsters


@router.get("/{monster_id}", response_model=Monster)
def get_monster(monster_id: int, session: Session = Depends(get_session)) -> Monster:
    monster = session.get(Monster, monster_id)
    if monster is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    return monster


@router.put("/{monster_id}", response_model=Monster)
def update_monster(monster_id: int, payload: Monster, session: Session = Depends(get_session)) -> Monster:
    monster = session.get(Monster, monster_id)
    if monster is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    monster.title = payload.title
    monster.description = payload.description
    monster.dangerous_lvl = payload.dangerous_lvl
    monster.hp = payload.hp
    monster.ac = payload.ac
    monster.speed = payload.speed
    session.add(monster)
    session.commit()
    session.refresh(monster)
    return monster


@router.delete("/{monster_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monster(monster_id: int, session: Session = Depends(get_session)) -> None:
    monster = session.get(Monster, monster_id)
    if monster is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    session.delete(monster)
    session.commit()
    return None



