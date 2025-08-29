import logging
from typing import List

from dnd_helper_api.db import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from shared_models import Monster

router = APIRouter(prefix="/monsters", tags=["monsters"])
logger = logging.getLogger(__name__)


@router.get("/search", response_model=List[Monster])
def search_monsters(q: str, session: Session = Depends(get_session)) -> List[Monster]:
    if not q:
        logger.warning("Empty monster search query")
        return []
    monsters = session.exec(
        select(Monster).where(Monster.title.ilike(f"%{q}%"))
    ).all()
    logger.info("Monster search completed", extra={"query": q, "count": len(monsters)})
    return monsters


@router.post("", response_model=Monster, status_code=status.HTTP_201_CREATED)
def create_monster(monster: Monster, session: Session = Depends(get_session)) -> Monster:
    # Ignore client-provided id
    monster.id = None
    session.add(monster)
    session.commit()
    session.refresh(monster)
    logger.info("Monster created", extra={"monster_id": monster.id, "title": monster.title})
    return monster


@router.get("", response_model=List[Monster])
def list_monsters(session: Session = Depends(get_session)) -> List[Monster]:
    monsters = session.exec(select(Monster)).all()
    logger.info("Monsters listed", extra={"count": len(monsters)})
    return monsters


@router.get("/{monster_id}", response_model=Monster)
def get_monster(monster_id: int, session: Session = Depends(get_session)) -> Monster:
    monster = session.get(Monster, monster_id)
    if monster is None:
        logger.warning("Monster not found", extra={"monster_id": monster_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    logger.info("Monster fetched", extra={"monster_id": monster_id})
    return monster


@router.put("/{monster_id}", response_model=Monster)
def update_monster(monster_id: int, payload: Monster, session: Session = Depends(get_session)) -> Monster:
    monster = session.get(Monster, monster_id)
    if monster is None:
        logger.warning("Monster not found for update", extra={"monster_id": monster_id})
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
    logger.info("Monster updated", extra={"monster_id": monster.id})
    return monster


@router.delete("/{monster_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monster(monster_id: int, session: Session = Depends(get_session)) -> None:
    monster = session.get(Monster, monster_id)
    if monster is None:
        logger.warning("Monster not found for delete", extra={"monster_id": monster_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    session.delete(monster)
    session.commit()
    logger.info("Monster deleted", extra={"monster_id": monster_id})
    return None



