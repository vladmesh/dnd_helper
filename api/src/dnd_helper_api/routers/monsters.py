import logging
from typing import List, Optional, Dict, Any

from dnd_helper_api.db import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from shared_models import Monster

router = APIRouter(prefix="/monsters", tags=["monsters"])
logger = logging.getLogger(__name__)


def _compute_monster_derived_fields(monster: Monster) -> None:
    """Populate derived fields on the Monster instance based on JSON fields.

    This is intentionally lightweight and defensive. Only sets fields when source
    data is present to avoid overwriting with incorrect defaults.
    """
    senses: Dict[str, Any] = monster.senses or {}

    # Helper
    def _as_int(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    # If scalar speed columns are provided directly, infer is_flying from speed_fly
    if monster.speed_fly is not None:
        monster.is_flying = monster.speed_fly > 0

    # Senses
    def _sense_pair(key: str) -> tuple[Optional[bool], Optional[int]]:
        rng = _as_int(senses.get(key)) if key in senses else None
        flag = (rng is not None and rng > 0) if key in senses else None
        return flag, rng

    has_darkvision, darkvision_range = _sense_pair("darkvision")
    has_blindsight, blindsight_range = _sense_pair("blindsight")
    has_truesight, truesight_range = _sense_pair("truesight")
    # tremorsense has only range column
    tremorsense_range = _as_int(senses.get("tremorsense")) if "tremorsense" in senses else None

    monster.has_darkvision = has_darkvision
    monster.darkvision_range = darkvision_range
    monster.has_blindsight = has_blindsight
    monster.blindsight_range = blindsight_range
    monster.has_truesight = has_truesight
    monster.truesight_range = truesight_range
    monster.tremorsense_range = tremorsense_range

    # slug generation from name if not provided
    if not getattr(monster, "slug", None) and getattr(monster, "name", None):
        monster.slug = _slugify(monster.name)


def _slugify(value: str) -> str:
    text = value.strip().lower()
    import re
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


@router.get("/search", response_model=List[Monster])
def search_monsters(
    q: str,
    type: Optional[str] = None,
    size: Optional[str] = None,
    cr_min: Optional[float] = None,
    cr_max: Optional[float] = None,
    is_flying: Optional[bool] = None,
    is_legendary: Optional[bool] = None,
    roles: Optional[List[str]] = None,
    environments: Optional[List[str]] = None,
    session: Session = Depends(get_session),
) -> List[Monster]:
    if not q:
        logger.warning("Empty monster search query")
        return []

    conditions = [Monster.name.ilike(f"%{q}%")]

    if type is not None:
        conditions.append(Monster.type == type)
    if size is not None:
        conditions.append(Monster.size == size)
    if cr_min is not None:
        conditions.append(Monster.cr >= cr_min)
    if cr_max is not None:
        conditions.append(Monster.cr <= cr_max)
    if is_flying is not None:
        conditions.append(Monster.is_flying == is_flying)
    if is_legendary is not None:
        conditions.append(Monster.is_legendary == is_legendary)
    if roles:
        conditions.append(Monster.roles.contains(roles))
    if environments:
        conditions.append(Monster.environments.contains(environments))

    monsters = session.exec(select(Monster).where(*conditions)).all()
    logger.info(
        "Monster search completed",
        extra={
            "query": q,
            "filters": {
                "type": type,
                "size": size,
                "cr_min": cr_min,
                "cr_max": cr_max,
                "is_flying": is_flying,
                "is_legendary": is_legendary,
                "roles": roles,
                "environments": environments,
            },
            "count": len(monsters),
        },
    )
    return monsters


@router.post("", response_model=Monster, status_code=status.HTTP_201_CREATED)
def create_monster(monster: Monster, session: Session = Depends(get_session)) -> Monster:
    # Ignore client-provided id
    monster.id = None
    _compute_monster_derived_fields(monster)
    session.add(monster)
    session.commit()
    session.refresh(monster)
    logger.info("Monster created", extra={"monster_id": monster.id, "monster_name": monster.name})
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
    monster.name = payload.name
    monster.description = payload.description
    monster.dangerous_lvl = payload.dangerous_lvl
    monster.hp = payload.hp
    monster.ac = payload.ac
    # legacy speed removed
    if payload.type is not None:
        monster.type = payload.type
    if payload.size is not None:
        monster.size = payload.size
    if payload.alignment is not None:
        monster.alignment = payload.alignment
    if payload.hit_dice is not None:
        monster.hit_dice = payload.hit_dice
    if payload.cr is not None:
        monster.cr = payload.cr
    if payload.xp is not None:
        monster.xp = payload.xp
    if payload.proficiency_bonus is not None:
        monster.proficiency_bonus = payload.proficiency_bonus
    if payload.abilities is not None:
        monster.abilities = payload.abilities
    if payload.saving_throws is not None:
        monster.saving_throws = payload.saving_throws
    if payload.skills is not None:
        monster.skills = payload.skills
    if payload.senses is not None:
        monster.senses = payload.senses
    if payload.languages is not None:
        monster.languages = payload.languages
    if payload.damage_immunities is not None:
        monster.damage_immunities = payload.damage_immunities
    if payload.damage_resistances is not None:
        monster.damage_resistances = payload.damage_resistances
    if payload.damage_vulnerabilities is not None:
        monster.damage_vulnerabilities = payload.damage_vulnerabilities
    if payload.condition_immunities is not None:
        monster.condition_immunities = payload.condition_immunities
    if payload.traits is not None:
        monster.traits = payload.traits
    if payload.actions is not None:
        monster.actions = payload.actions
    if payload.reactions is not None:
        monster.reactions = payload.reactions
    if payload.legendary_actions is not None:
        monster.legendary_actions = payload.legendary_actions
    if payload.spellcasting is not None:
        monster.spellcasting = payload.spellcasting
    if payload.tags is not None:
        monster.tags = payload.tags
    _compute_monster_derived_fields(monster)
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



