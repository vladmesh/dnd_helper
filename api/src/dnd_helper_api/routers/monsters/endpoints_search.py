from typing import Any, Dict, List, Optional
from enum import Enum

from dnd_helper_api.db import get_session
from dnd_helper_api.routers.monsters import logger, router
from dnd_helper_api.utils.enum_labels import resolve_enum_labels
from fastapi import Depends, Response, Query
from sqlmodel import Session, select
from sqlalchemy import or_

from shared_models import Monster
from shared_models.monster_translation import MonsterTranslation

from .translations import (
    _apply_monster_translations_bulk,
    _effective_monster_translation_dict,
    _select_language,
)


class SearchScope(str, Enum):
    NAME = "name"
    NAME_DESCRIPTION = "name_description"

## Removed legacy search endpoint '/monsters/search'


## Removed legacy search endpoint '/monsters/search-wrapped'



@router.get("/search/raw", response_model=List[Monster])
def search_monsters_raw(
    q: str,
    type: Optional[str] = None,
    size: Optional[str] = None,
    cr_min: Optional[float] = None,
    cr_max: Optional[float] = None,
    is_flying: Optional[bool] = None,
    is_legendary: Optional[bool] = None,
    roles: Optional[List[str]] = None,
    environments: Optional[List[str]] = None,
    search_scope: SearchScope = Query(SearchScope.NAME),
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Monster]:
    if not q:
        logger.warning("Empty monster search query")
        return []
    conditions: List[Any] = []
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

    requested_lang = _select_language(lang)
    pattern = f"%{q.strip()}%"
    search_condition = (
        MonsterTranslation.name.ilike(pattern)
        if search_scope == SearchScope.NAME
        else or_(
            MonsterTranslation.name.ilike(pattern),
            MonsterTranslation.description.ilike(pattern),
        )
    )
    stmt = (
        select(Monster)
        .join(MonsterTranslation, MonsterTranslation.monster_id == Monster.id)
        .where(
            MonsterTranslation.lang == requested_lang,
            search_condition,
            *conditions,
        )
        .distinct()
    )
    monsters = session.exec(stmt).all()
    _apply_monster_translations_bulk(session, monsters, lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
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


@router.get("/search/wrapped", response_model=List[Dict[str, Any]])
def search_monsters_wrapped(
    q: str,
    type: Optional[str] = None,
    size: Optional[str] = None,
    cr_min: Optional[float] = None,
    cr_max: Optional[float] = None,
    is_flying: Optional[bool] = None,
    is_legendary: Optional[bool] = None,
    roles: Optional[List[str]] = None,
    environments: Optional[List[str]] = None,
    search_scope: SearchScope = Query(SearchScope.NAME),
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Dict[str, Any]]:
    if not q:
        logger.warning("Empty monster search (wrapped) query")
        return []

    conditions: List[Any] = []
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

    requested_lang = _select_language(lang)
    pattern = f"%{q.strip()}%"
    search_condition = (
        MonsterTranslation.name.ilike(pattern)
        if search_scope == SearchScope.NAME
        else or_(
            MonsterTranslation.name.ilike(pattern),
            MonsterTranslation.description.ilike(pattern),
        )
    )
    stmt = (
        select(Monster)
        .join(MonsterTranslation, MonsterTranslation.monster_id == Monster.id)
        .where(
            MonsterTranslation.lang == requested_lang,
            search_condition,
            *conditions,
        )
        .distinct()
    )
    monsters = session.exec(stmt).all()

    codes = {
        "monster_type": {str(m.type).lower() for m in monsters if m.type},
        "monster_size": {str(m.size).lower() for m in monsters if m.size},
        "danger_level": {str(m.cr) for m in monsters if m.cr},
    }
    labels = resolve_enum_labels(session, requested_lang, codes)

    result: List[Dict[str, Any]] = []
    for m in monsters:
        result.append(
            {
                "entity": m.model_dump(),
                "translation": _effective_monster_translation_dict(session, int(m.id), lang) if m.id is not None else None,
                "labels": {
                    **({"type": {"code": str(m.type).lower(), "label": labels.get(("monster_type", str(m.type).lower()), str(m.type))} if m.type else {}}),
                    **({"size": {"code": str(m.size).lower(), "label": labels.get(("monster_size", str(m.size).lower()), str(m.size))} if m.size else {}}),
                    **({"cr": {"code": str(m.cr), "label": labels.get(("danger_level", str(m.cr)), str(m.cr))} if m.cr else {}}),
                },
            }
        )
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    logger.info("Monsters search-wrapped completed", extra={"query": q, "count": len(result)})
    return result

