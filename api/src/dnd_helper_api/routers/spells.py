import logging
from typing import List

from dnd_helper_api.db import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from shared_models import Spell

router = APIRouter(prefix="/spells", tags=["spells"])
logger = logging.getLogger(__name__)


@router.get("/search", response_model=List[Spell])
def search_spells(q: str, session: Session = Depends(get_session)) -> List[Spell]:
    if not q:
        logger.warning("Empty spell search query")
        return []
    spells = session.exec(
        select(Spell).where(Spell.title.ilike(f"%{q}%"))
    ).all()
    logger.info("Spell search completed", extra={"query": q, "count": len(spells)})
    return spells


@router.post("", response_model=Spell, status_code=status.HTTP_201_CREATED)
def create_spell(spell: Spell, session: Session = Depends(get_session)) -> Spell:
    spell.id = None
    session.add(spell)
    session.commit()
    session.refresh(spell)
    logger.info("Spell created", extra={"spell_id": spell.id, "title": spell.title})
    return spell


@router.get("", response_model=List[Spell])
def list_spells(session: Session = Depends(get_session)) -> List[Spell]:
    spells = session.exec(select(Spell)).all()
    logger.info("Spells listed", extra={"count": len(spells)})
    return spells


@router.get("/{spell_id}", response_model=Spell)
def get_spell(spell_id: int, session: Session = Depends(get_session)) -> Spell:
    spell = session.get(Spell, spell_id)
    if spell is None:
        logger.warning("Spell not found", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    logger.info("Spell fetched", extra={"spell_id": spell_id})
    return spell


@router.put("/{spell_id}", response_model=Spell)
def update_spell(spell_id: int, payload: Spell, session: Session = Depends(get_session)) -> Spell:
    spell = session.get(Spell, spell_id)
    if spell is None:
        logger.warning("Spell not found for update", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    spell.title = payload.title
    spell.description = payload.description
    spell.caster_class = payload.caster_class
    spell.distance = payload.distance
    spell.school = payload.school
    session.add(spell)
    session.commit()
    session.refresh(spell)
    logger.info("Spell updated", extra={"spell_id": spell.id})
    return spell


@router.delete("/{spell_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spell(spell_id: int, session: Session = Depends(get_session)) -> None:
    spell = session.get(Spell, spell_id)
    if spell is None:
        logger.warning("Spell not found for delete", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    session.delete(spell)
    session.commit()
    logger.info("Spell deleted", extra={"spell_id": spell_id})
    return None



