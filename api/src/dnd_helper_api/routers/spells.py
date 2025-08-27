from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from shared_models import Spell
from dnd_helper_api.db import get_session


router = APIRouter(prefix="/spells", tags=["spells"])


@router.post("", response_model=Spell, status_code=status.HTTP_201_CREATED)
def create_spell(spell: Spell, session: Session = Depends(get_session)) -> Spell:
    spell.id = None
    session.add(spell)
    session.commit()
    session.refresh(spell)
    return spell


@router.get("", response_model=List[Spell])
def list_spells(session: Session = Depends(get_session)) -> List[Spell]:
    spells = session.exec(select(Spell)).all()
    return spells


@router.get("/{spell_id}", response_model=Spell)
def get_spell(spell_id: int, session: Session = Depends(get_session)) -> Spell:
    spell = session.get(Spell, spell_id)
    if spell is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    return spell


@router.put("/{spell_id}", response_model=Spell)
def update_spell(spell_id: int, payload: Spell, session: Session = Depends(get_session)) -> Spell:
    spell = session.get(Spell, spell_id)
    if spell is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    spell.title = payload.title
    spell.description = payload.description
    spell.caster_class = payload.caster_class
    spell.distance = payload.distance
    spell.school = payload.school
    session.add(spell)
    session.commit()
    session.refresh(spell)
    return spell


@router.delete("/{spell_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spell(spell_id: int, session: Session = Depends(get_session)) -> None:
    spell = session.get(Spell, spell_id)
    if spell is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    session.delete(spell)
    session.commit()
    return None



