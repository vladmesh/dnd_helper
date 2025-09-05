from typing import Any, Dict, List, Optional

from fastapi import Depends, Response, status
from sqlmodel import Session, select

from dnd_helper_api.db import get_session
from dnd_helper_api.routers.monsters import router, logger
from dnd_helper_api.utils.enum_labels import resolve_enum_labels
from shared_models import Monster
from shared_models.enums import Language

from .translations import (
    _select_language,
    _effective_monster_translation_dict,
)


def _with_labels(monster: Monster, labels: Dict[tuple[str, str], str]) -> Dict[str, Any]:
    body = monster.model_dump()
    name = getattr(monster, "name", None)
    if name is not None:
        body["name"] = name
    description = getattr(monster, "description", None)
    if description is not None:
        body["description"] = description
    t = body.get("type")
    if t:
        code = str(t).lower()
        body["type"] = {"code": code, "label": labels.get(("monster_type", code), str(t))}
    s = body.get("size")
    if s:
        code = str(s).lower()
        body["size"] = {"code": code, "label": labels.get(("monster_size", code), str(s))}
    cr = body.get("cr")
    if cr:
        code = str(cr)
        body["cr"] = {"code": code, "label": labels.get(("danger_level", code), code)}
    return body


@router.get("", response_model=List[Monster])
def list_monsters(
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Monster]:
    monsters = session.exec(select(Monster)).all()
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    logger.info("Monsters listed", extra={"count": len(monsters)})
    return monsters


@router.get("/wrapped-list", response_model=List[Dict[str, Any]])
def list_monsters_wrapped(
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Dict[str, Any]]:
    monsters = session.exec(select(Monster)).all()
    # Keep output consistent with legacy behavior: include effective translation
    # Do not mutate entities here to avoid double-work; compute translation payloads instead
    requested_lang: Language = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
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
    logger.info("Monsters wrapped listed", extra={"count": len(result)})
    return result


