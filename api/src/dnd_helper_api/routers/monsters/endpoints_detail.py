from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Response, status
from sqlmodel import Session, select

from dnd_helper_api.db import get_session
from dnd_helper_api.routers.monsters import router, logger
from dnd_helper_api.utils.enum_labels import resolve_enum_labels
from shared_models import Monster

from .translations import _effective_monster_translation_dict, _select_language


@router.get("/{monster_id}", response_model=Monster)
def get_monster(
    monster_id: int,
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> Monster:
    monster = session.get(Monster, monster_id)
    if monster is None:
        logger.warning("Monster not found", extra={"monster_id": monster_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    logger.info("Monster fetched", extra={"monster_id": monster_id})
    return monster


@router.get("/{monster_id}/wrapped", response_model=Dict[str, Any])
def get_monster_wrapped(
    monster_id: int,
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> Dict[str, Any]:
    m = session.get(Monster, monster_id)
    if m is None:
        logger.warning("Monster not found (wrapped)", extra={"monster_id": monster_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    codes = {
        "monster_type": {str(m.type).lower()} if m.type else set(),
        "monster_size": {str(m.size).lower()} if m.size else set(),
        "danger_level": {str(m.cr)} if m.cr else set(),
    }
    labels = resolve_enum_labels(session, requested_lang, codes)
    body = {
        "entity": m.model_dump(),
        "translation": _effective_monster_translation_dict(session, monster_id, lang),
        "labels": {
            **({"type": {"code": str(m.type).lower(), "label": labels.get(("monster_type", str(m.type).lower()), str(m.type))} if m.type else {}}),
            **({"size": {"code": str(m.size).lower(), "label": labels.get(("monster_size", str(m.size).lower()), str(m.size))} if m.size else {}}),
            **({"cr": {"code": str(m.cr), "label": labels.get(("danger_level", str(m.cr)), str(m.cr))} if m.cr else {}}),
        },
    }
    logger.info("Monster wrapped fetched", extra={"monster_id": monster_id})
    return body


