import logging
from typing import List, Optional, Dict, Any

from dnd_helper_api.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
from sqlalchemy import or_

from shared_models import Spell

router = APIRouter(prefix="/spells", tags=["spells"])
logger = logging.getLogger(__name__)


def _compute_spell_derived_fields(spell: Spell) -> None:
    """Populate derived fast-filter fields for Spell based on simple heuristics.

    Keep logic minimal and defensive: only set flags when source data is present.
    """
    # slug generation from name if not provided
    if not getattr(spell, "slug", None) and getattr(spell, "name", None):
        spell.slug = _slugify(spell.name)

    # is_concentration from duration string
    if spell.duration is not None:
        dur = str(spell.duration).lower()
        spell.is_concentration = ("concentration" in dur)

    # damage_type from damage JSON
    damage: Dict[str, Any] = spell.damage or {}
    if isinstance(damage, dict) and damage.get("type") is not None:
        spell.damage_type = str(damage.get("type"))

    # save_ability from saving_throw JSON
    saving_throw: Dict[str, Any] = spell.saving_throw or {}
    if isinstance(saving_throw, dict) and saving_throw.get("ability") is not None:
        spell.save_ability = str(saving_throw.get("ability"))

    # attack_roll heuristic: explicit flag if present in damage/area, else None
    # If damage exists and no saving_throw ability, many spells require an attack roll
    if spell.attack_roll is None:
        if damage and not saving_throw.get("ability"):
            spell.attack_roll = True

    # targeting heuristic: if area present, infer POINT else CREATURE(S) when tags suggest
    if spell.targeting is None:
        area = spell.area or {}
        if area:
            spell.targeting = "POINT"

    # normalize casting_time to a finite set
    if spell.casting_time is not None:
        spell.casting_time = _normalize_casting_time(str(spell.casting_time))


def _slugify(value: str) -> str:
    text = value.strip().lower()
    # Replace non-alphanumeric with hyphens
    import re
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _normalize_casting_time(value: str) -> str:
    v = value.strip().lower()
    # Priority: bonus action / reaction
    if "bonus action" in v:
        return "bonus_action"
    if "reaction" in v:
        return "reaction"
    # 1 action
    if v == "action" or "1 action" in v:
        return "action"
    # minutes
    if "10 minute" in v or "10 min" in v or v.startswith("10m"):
        return "10m"
    if "1 minute" in v or "1 min" in v or v.startswith("1m"):
        return "1m"
    # hours
    if "8 hour" in v or v.startswith("8h"):
        return "8h"
    if "1 hour" in v or v.startswith("1h"):
        return "1h"
    return v

@router.get("/search", response_model=List[Spell])
def search_spells(
    q: str,
    level: Optional[int] = None,
    school: Optional[str] = None,
    klass: Optional[str] = Query(None, alias="class"),
    damage_type: Optional[str] = None,
    save_ability: Optional[str] = None,
    attack_roll: Optional[bool] = None,
    ritual: Optional[bool] = None,
    is_concentration: Optional[bool] = None,
    targeting: Optional[str] = None,
    tags: Optional[List[str]] = None,
    session: Session = Depends(get_session),
) -> List[Spell]:
    if not q:
        logger.warning("Empty spell search query")
        return []

    conditions = [Spell.name.ilike(f"%{q}%")]

    if level is not None:
        conditions.append(Spell.level == level)
    if school is not None:
        conditions.append(Spell.school == school)
    if klass is not None:
        conditions.append(Spell.classes.contains([klass]))
    if damage_type is not None:
        conditions.append(Spell.damage_type == damage_type)
    if save_ability is not None:
        conditions.append(Spell.save_ability == save_ability)
    if attack_roll is not None:
        conditions.append(Spell.attack_roll == attack_roll)
    if ritual is not None:
        conditions.append(Spell.ritual == ritual)
    if is_concentration is not None:
        conditions.append(Spell.is_concentration == is_concentration)
    if targeting is not None:
        conditions.append(Spell.targeting == targeting)
    if tags:
        conditions.append(Spell.tags.contains(tags))

    spells = session.exec(select(Spell).where(*conditions)).all()
    logger.info(
        "Spell search completed",
        extra={
            "query": q,
            "filters": {
                "level": level,
                "school": school,
                "class": klass,
                "damage_type": damage_type,
                "save_ability": save_ability,
                "attack_roll": attack_roll,
                "ritual": ritual,
                "is_concentration": is_concentration,
                "targeting": targeting,
                "tags": tags,
            },
            "count": len(spells),
        },
    )
    return spells


@router.post("", response_model=Spell, status_code=status.HTTP_201_CREATED)
def create_spell(spell: Spell, session: Session = Depends(get_session)) -> Spell:
    spell.id = None
    _compute_spell_derived_fields(spell)
    session.add(spell)
    session.commit()
    session.refresh(spell)
    logger.info("Spell created", extra={"spell_id": spell.id, "spell_name": spell.name})
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
    spell.name = payload.name
    spell.description = payload.description
    spell.caster_class = payload.caster_class
    # legacy distance removed
    spell.school = payload.school
    if payload.level is not None:
        spell.level = payload.level
    if payload.ritual is not None:
        spell.ritual = payload.ritual
    if payload.casting_time is not None:
        spell.casting_time = payload.casting_time
    if payload.range is not None:
        spell.range = payload.range
    if payload.duration is not None:
        spell.duration = payload.duration
    if payload.concentration is not None:
        spell.concentration = payload.concentration
    if payload.components is not None:
        spell.components = payload.components
    if payload.classes is not None:
        spell.classes = payload.classes
    if payload.damage is not None:
        spell.damage = payload.damage
    if payload.saving_throw is not None:
        spell.saving_throw = payload.saving_throw
    if payload.area is not None:
        spell.area = payload.area
    if payload.conditions is not None:
        spell.conditions = payload.conditions
    if payload.tags is not None:
        spell.tags = payload.tags
    _compute_spell_derived_fields(spell)
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



