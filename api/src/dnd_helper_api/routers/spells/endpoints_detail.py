from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Response, status
from sqlmodel import Session

from dnd_helper_api.db import get_session
from dnd_helper_api.routers.spells import router, logger
from dnd_helper_api.utils.enum_labels import resolve_enum_labels
from shared_models import Spell

from .translations import _apply_spell_translation, _effective_spell_translation_dict, _select_language


@router.get("/{spell_id}", response_model=Spell)
def get_spell(
    spell_id: int,
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> Spell:
    spell = session.get(Spell, spell_id)
    if spell is None:
        logger.warning("Spell not found", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    _apply_spell_translation(session, spell, lang)
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    logger.info("Spell fetched", extra={"spell_id": spell_id})
    return spell


@router.get("/{spell_id}/wrapped", response_model=Dict[str, Any])
def get_spell_wrapped(
    spell_id: int,
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> Dict[str, Any]:
    s = session.get(Spell, spell_id)
    if s is None:
        logger.warning("Spell not found (wrapped)", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    codes = {
        "spell_school": {str(s.school)} if s.school else set(),
        "caster_class": set(s.classes or []),
    }
    labels = resolve_enum_labels(session, requested_lang, codes)
    body = {
        "entity": s.model_dump(),
        "translation": _effective_spell_translation_dict(session, spell_id, lang),
        "labels": {
            **({"school": {"code": str(s.school), "label": labels.get(("spell_school", str(s.school)), str(s.school))} if s.school else {}}),
            **({"classes": [
                {"code": c, "label": labels.get(("caster_class", str(c)), str(c))}
                for c in (s.classes or [])
            ]} if s.classes else {}),
        },
    }
    logger.info("Spell wrapped fetched", extra={"spell_id": spell_id})
    return body


