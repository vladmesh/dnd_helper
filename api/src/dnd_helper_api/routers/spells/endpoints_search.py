from enum import Enum
from typing import Any, Dict, List, Optional

from dnd_helper_api.db import get_session
from dnd_helper_api.routers.spells import logger, router
from dnd_helper_api.utils.enum_labels import resolve_enum_labels
from fastapi import Depends, Query, Response
from sqlalchemy import or_
from sqlmodel import Session, select

from shared_models import Spell
from shared_models.spell_translation import SpellTranslation

from .translations import (
    _apply_spell_translations_bulk,
    _effective_spell_translation_dict,
    _select_language,
)


class SearchScope(str, Enum):
    NAME = "name"
    NAME_DESCRIPTION = "name_description"

## Removed legacy search endpoint '/spells/search'
@router.get("/search/raw", response_model=List[Spell])
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
    search_scope: SearchScope = Query(SearchScope.NAME),
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Spell]:
    if not q:
        logger.warning("Empty spell search query")
        return []
    conditions: List[Any] = []
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

    requested_lang = _select_language(lang)
    pattern = f"%{q.strip()}%"
    search_condition = (
        SpellTranslation.name.ilike(pattern)
        if search_scope == SearchScope.NAME
        else or_(
            SpellTranslation.name.ilike(pattern),
            SpellTranslation.description.ilike(pattern),
        )
    )
    stmt = (
        select(Spell)
        .join(SpellTranslation, SpellTranslation.spell_id == Spell.id)
        .where(
            SpellTranslation.lang == requested_lang,
            search_condition,
            *conditions,
        )
        .distinct()
    )
    spells = session.exec(stmt).all()
    _apply_spell_translations_bulk(session, spells, lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
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


## Removed legacy search endpoint '/spells/search-wrapped'
@router.get("/search/wrapped", response_model=List[Dict[str, Any]])
def search_spells_wrapped(
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
    search_scope: SearchScope = Query(SearchScope.NAME),
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Dict[str, Any]]:
    if not q:
        logger.warning("Empty spell search (wrapped) query")
        return []

    conditions: List[Any] = []
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

    requested_lang = _select_language(lang)
    pattern = f"%{q.strip()}%"
    search_condition = (
        SpellTranslation.name.ilike(pattern)
        if search_scope == SearchScope.NAME
        else or_(
            SpellTranslation.name.ilike(pattern),
            SpellTranslation.description.ilike(pattern),
        )
    )
    stmt = (
        select(Spell)
        .join(SpellTranslation, SpellTranslation.spell_id == Spell.id)
        .where(
            SpellTranslation.lang == requested_lang,
            search_condition,
            *conditions,
        )
        .distinct()
    )
    spells = session.exec(stmt).all()

    codes = {
        "spell_school": {str(s.school) for s in spells if s.school},
        "caster_class": {c for s in spells for c in (s.classes or [])},
    }
    labels = resolve_enum_labels(session, requested_lang, codes)

    result: List[Dict[str, Any]] = []
    for s in spells:
        result.append(
            {
                "entity": s.model_dump(),
                "translation": _effective_spell_translation_dict(session, int(s.id), lang) if s.id is not None else None,
                "labels": {
                    **({"school": {"code": str(s.school), "label": labels.get(("spell_school", str(s.school)), str(s.school))} if s.school else {}}),
                    **({"classes": [
                        {"code": c, "label": labels.get(("caster_class", str(c)), str(c))}
                        for c in (s.classes or [])
                    ]} if s.classes else {}),
                },
            }
        )
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    logger.info("Spells search-wrapped completed", extra={"query": q, "count": len(result)})
    return result



## Removed alias indirection: '/search/raw' is primary now
@router.get("/search/raw", response_model=List[Spell])
def search_spells_alias_raw(
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
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Spell]:
    return search_spells(
        q=q,
        level=level,
        school=school,
        klass=klass,
        damage_type=damage_type,
        save_ability=save_ability,
        attack_roll=attack_roll,
        ritual=ritual,
        is_concentration=is_concentration,
        targeting=targeting,
        tags=tags,
        lang=lang,
        session=session,
        response=response,
    )


## Removed alias indirection: '/search/wrapped' is primary now
@router.get("/search/wrapped", response_model=List[Dict[str, Any]])
def search_spells_alias_wrapped(
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
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Dict[str, Any]]:
    """Alias for /spells/search-wrapped (wrapped search)."""
    return search_spells_wrapped(
        q=q,
        level=level,
        school=school,
        klass=klass,
        damage_type=damage_type,
        save_ability=save_ability,
        attack_roll=attack_roll,
        ritual=ritual,
        is_concentration=is_concentration,
        targeting=targeting,
        tags=tags,
        lang=lang,
        session=session,
        response=response,
    )

