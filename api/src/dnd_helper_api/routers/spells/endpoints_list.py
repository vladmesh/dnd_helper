from typing import Any, Dict, List, Optional

from fastapi import Depends, Response
from sqlmodel import Session, select

from dnd_helper_api.db import get_session
from dnd_helper_api.routers.spells import router, logger
from dnd_helper_api.utils.enum_labels import resolve_enum_labels
from shared_models import Spell

from .translations import _effective_spell_translation_dict, _select_language


def _with_labels(spell: Spell, labels: Dict[tuple[str, str], str]) -> Dict[str, Any]:
    body = spell.model_dump()
    name = getattr(spell, "name", None)
    if name is not None:
        body["name"] = name
    description = getattr(spell, "description", None)
    if description is not None:
        body["description"] = description
    code = body.get("school")
    if code:
        body["school"] = {"code": code, "label": labels.get(("spell_school", str(code)), str(code))}
    classes = body.get("classes") or []
    body["classes"] = [
        {"code": c, "label": labels.get(("caster_class", str(c)), str(c))} for c in classes
    ]
    return body


@router.get("", response_model=List[Spell])
def list_spells(
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Spell]:
    spells = session.exec(select(Spell)).all()
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    logger.info("Spells listed", extra={"count": len(spells)})
    return spells


@router.get("/labeled", response_model=List[Dict[str, Any]])
def list_spells_labeled(
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Dict[str, Any]]:
    spells = session.exec(select(Spell)).all()
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    codes = {
        "spell_school": {str(s.school) for s in spells if s.school},
        "caster_class": {c for s in spells for c in (s.classes or [])},
    }
    labels = resolve_enum_labels(session, requested_lang, codes)
    return [_with_labels(s, labels) for s in spells]


@router.get("/wrapped", response_model=List[Dict[str, Any]])
def list_spells_wrapped(
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Dict[str, Any]]:
    spells = session.exec(select(Spell)).all()
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
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
    logger.info("Spells wrapped listed", extra={"count": len(result)})
    return result


@router.get("/wrapped-list", response_model=List[Dict[str, Any]])
def list_spells_wrapped_list(
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Dict[str, Any]]:
    """Alias for /spells/wrapped for consistency with monsters endpoints."""
    return list_spells_wrapped(lang=lang, session=session, response=response)


