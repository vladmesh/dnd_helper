import logging
from typing import Any, Dict, List, Optional

from dnd_helper_api.db import get_session
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy import delete
from sqlmodel import Session, select

from shared_models import Monster
from shared_models.enums import Language
from shared_models.monster_translation import MonsterTranslation
from pydantic import BaseModel
from dnd_helper_api.utils.enum_labels import resolve_enum_labels

router = APIRouter(prefix="/monsters", tags=["monsters"])
logger = logging.getLogger(__name__)


def _select_language(lang: Optional[str]) -> Language:
    try:
        if isinstance(lang, str):
            val = lang.strip().lower()
            if val in {"ru", "en"}:
                return Language(val)
    except Exception:
        pass
    return Language.RU


def _fallback_language(primary: Language) -> Language:
    return Language.EN if primary == Language.RU else Language.RU


def _apply_monster_translation(
    session: Session,
    monster: Monster,
    lang: Optional[str],
) -> None:
    """Apply localized name/description to a Monster instance in-place.

    Fallback to the other available language if primary not found. Silent if no translations.
    """
    primary = _select_language(lang)
    fallback = _fallback_language(primary)

    tr = session.exec(
        select(MonsterTranslation).where(
            MonsterTranslation.monster_id == monster.id,
            MonsterTranslation.lang == primary,
        )
    ).first()
    if tr is None:
        tr = session.exec(
            select(MonsterTranslation).where(
                MonsterTranslation.monster_id == monster.id,
                MonsterTranslation.lang == fallback,
            )
        ).first()
    if tr is not None:
        # Assign only if attributes exist on model (post-i18n cleanup)
        for attr, value in (
            ("name", tr.name),
            ("description", tr.description),
            ("traits", tr.traits),
            ("actions", tr.actions),
            ("reactions", tr.reactions),
            ("legendary_actions", tr.legendary_actions),
            ("spellcasting", tr.spellcasting),
        ):
            try:
                setattr(monster, attr, value)  # type: ignore[attr-defined]
            except Exception:
                pass


def _apply_monster_translations_bulk(
    session: Session,
    monsters: List[Monster],
    lang: Optional[str],
) -> None:
    """Apply localized fields to a list of monsters in batch to avoid N+1."""
    if not monsters:
        return
    primary = _select_language(lang)
    fallback = _fallback_language(primary)
    monster_ids = [m.id for m in monsters if m.id is not None]
    if not monster_ids:
        return
    rows = session.exec(
        select(MonsterTranslation).where(
            MonsterTranslation.monster_id.in_(monster_ids),
            MonsterTranslation.lang.in_([primary, fallback]),
        )
    ).all()
    # Map: monster_id -> {lang: translation}
    by_monster: Dict[int, Dict[Language, MonsterTranslation]] = {}
    for r in rows:
        by_monster.setdefault(r.monster_id, {})[r.lang] = r

    for m in monsters:
        if m.id is None:
            continue
        lang_map = by_monster.get(m.id) or {}
        tr = lang_map.get(primary) or lang_map.get(fallback)
        if tr is None:
            continue
        for attr, value in (
            ("name", tr.name),
            ("description", tr.description),
            ("traits", tr.traits),
            ("actions", tr.actions),
            ("reactions", tr.reactions),
            ("legendary_actions", tr.legendary_actions),
            ("spellcasting", tr.spellcasting),
        ):
            try:
                setattr(m, attr, value)  # type: ignore[attr-defined]
            except Exception:
                pass


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

    # slug generation from name removed (name is localized)


def _slugify(value: str) -> str:
    text = value.strip().lower()
    import re
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# @router.get("/search", response_model=List[Monster])
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
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Monster]:
    if not q:
        logger.warning("Empty monster search query")
        return []

    # Base table no longer has name; this endpoint no longer supports name substring search
    return []

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
    # Apply translations and expose effective language
    _apply_monster_translations_bulk(session, monsters, lang)
    requested_lang = _select_language(lang)
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


@router.post("", response_model=Monster, status_code=status.HTTP_201_CREATED)
async def create_monster(
    monster: Monster,
    lang: Optional[str] = None,
    request: Request = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> Monster:
    # Ignore client-provided id
    monster.id = None
    _compute_monster_derived_fields(monster)
    session.add(monster)
    session.commit()
    session.refresh(monster)
    # Upsert translations from payload if provided; else map scalar name/description into selected lang
    try:
        body = await request.json() if request is not None else {}
    except Exception:
        body = {}
    translations = body.get("translations") if isinstance(body, dict) else None

    if isinstance(translations, dict):
        for lang_code in ("ru", "en"):
            data = translations.get(lang_code)
            if isinstance(data, dict) and (data.get("name") and data.get("description") or any(k in data for k in ("traits","actions","reactions","legendary_actions","spellcasting"))):
                l = _select_language(lang_code)
                existing = session.exec(
                    select(MonsterTranslation).where(
                        MonsterTranslation.monster_id == monster.id,
                        MonsterTranslation.lang == l,
                    )
                ).first()
                if existing is None:
                    session.add(
                        MonsterTranslation(
                            monster_id=monster.id,
                            lang=l,
                            name=(data.get("name") or ""),
                            description=(data.get("description") if data.get("description") is not None else ""),
                            traits=data.get("traits"),
                            actions=data.get("actions"),
                            reactions=data.get("reactions"),
                            legendary_actions=data.get("legendary_actions"),
                            spellcasting=data.get("spellcasting"),
                        )
                    )
                else:
                    if data.get("name"):
                        existing.name = data["name"]
                    if data.get("description"):
                        existing.description = data["description"]
                    existing.traits = data.get("traits")
                    existing.actions = data.get("actions")
                    existing.reactions = data.get("reactions")
                    existing.legendary_actions = data.get("legendary_actions")
                    existing.spellcasting = data.get("spellcasting")
                    session.add(existing)
        session.commit()
    else:
        # No translations provided; keep existing translations unchanged
        pass

    logger.info("Monster created", extra={"monster_id": monster.id})
    return monster


# @router.get("", response_model=List[Monster])
def list_monsters(
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Monster]:
    monsters = session.exec(select(Monster)).all()
    _apply_monster_translations_bulk(session, monsters, lang)
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    logger.info("Monsters listed", extra={"count": len(monsters)})
    return monsters


def _with_labels(monster: Monster, labels: Dict[tuple[str, str], str]) -> Dict[str, Any]:
    body = monster.model_dump()
    # Include translated fields applied in-place (they are not part of ORM schema)
    name = getattr(monster, "name", None)
    if name is not None:
        body["name"] = name
    description = getattr(monster, "description", None)
    if description is not None:
        body["description"] = description
    # Normalize codes to lowercase for lookup
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


# @router.get("/labeled", response_model=List[Dict[str, Any]])
def list_monsters_labeled(
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Dict[str, Any]]:
    monsters = session.exec(select(Monster)).all()
    _apply_monster_translations_bulk(session, monsters, lang)
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    codes = {
        "monster_type": {str(m.type).lower() for m in monsters if m.type},
        "monster_size": {str(m.size).lower() for m in monsters if m.size},
        "danger_level": {str(m.cr) for m in monsters if m.cr},
    }
    labels = resolve_enum_labels(session, requested_lang, codes)
    return [_with_labels(m, labels) for m in monsters]


# @router.get("/{monster_id}", response_model=Monster)
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
    _apply_monster_translation(session, monster, lang)
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    logger.info("Monster fetched", extra={"monster_id": monster_id})
    return monster

# @router.get("/{monster_id}/labeled", response_model=Dict[str, Any])
def get_monster_labeled(
    monster_id: int,
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> Dict[str, Any]:
    monster = session.get(Monster, monster_id)
    if monster is None:
        logger.warning("Monster not found", extra={"monster_id": monster_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    _apply_monster_translation(session, monster, lang)
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    codes = {
        "monster_type": {str(monster.type).lower()} if monster.type else set(),
        "monster_size": {str(monster.size).lower()} if monster.size else set(),
        "danger_level": {str(monster.cr)} if monster.cr else set(),
    }
    labels = resolve_enum_labels(session, requested_lang, codes)
    return _with_labels(monster, labels)


@router.put("/{monster_id}", response_model=Monster)
async def update_monster(
    monster_id: int,
    payload: Monster,
    lang: Optional[str] = None,
    request: Request = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> Monster:
    monster = session.get(Monster, monster_id)
    if monster is None:
        logger.warning("Monster not found for update", extra={"monster_id": monster_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    # name/description moved to translations; skip base assignment
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
    # localized blocks moved to translations; skip base assignment
    if payload.tags is not None:
        monster.tags = payload.tags
    _compute_monster_derived_fields(monster)
    session.add(monster)
    session.commit()
    session.refresh(monster)

    # Upsert translations from payload if provided; else map scalar name/description into selected lang
    try:
        body = await request.json() if request is not None else {}
    except Exception:
        body = {}
    translations = body.get("translations") if isinstance(body, dict) else None

    if isinstance(translations, dict):
        for lang_code in ("ru", "en"):
            data = translations.get(lang_code)
            if isinstance(data, dict) and data.get("name") and data.get("description"):
                l = _select_language(lang_code)
                existing = session.exec(
                    select(MonsterTranslation).where(
                        MonsterTranslation.monster_id == monster.id,
                        MonsterTranslation.lang == l,
                    )
                ).first()
                if existing is None:
                    session.add(
                        MonsterTranslation(
                            monster_id=monster.id,
                            lang=l,
                            name=data["name"],
                            description=data["description"],
                        )
                    )
                else:
                    existing.name = data["name"]
                    existing.description = data["description"]
                    session.add(existing)
        session.commit()
    else:
        # No translations provided; keep existing translations unchanged
        pass
    logger.info("Monster updated", extra={"monster_id": monster.id})
    return monster


@router.delete("/{monster_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monster(
    monster_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> None:
    monster = session.get(Monster, monster_id)
    if monster is None:
        logger.warning("Monster not found for delete", extra={"monster_id": monster_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    # Delete translations first to satisfy FK constraints
    session.exec(
        delete(MonsterTranslation).where(MonsterTranslation.monster_id == monster_id)
    )
    session.delete(monster)
    session.commit()
    logger.info("Monster deleted", extra={"monster_id": monster_id})
    return None


class MonsterTranslationUpsert(BaseModel):
    lang: str
    name: str
    description: str


@router.post("/{monster_id}/translations", status_code=status.HTTP_204_NO_CONTENT)
def upsert_monster_translation(
    monster_id: int,
    body: MonsterTranslationUpsert,
    session: Session = Depends(get_session),  # noqa: B008
) -> None:
    monster = session.get(Monster, monster_id)
    if monster is None:
        logger.warning("Monster not found for translation upsert", extra={"monster_id": monster_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")

    lang = _select_language(body.lang)

    existing = session.exec(
        select(MonsterTranslation).where(
            MonsterTranslation.monster_id == monster_id,
            MonsterTranslation.lang == lang,
        )
    ).first()

    if existing is None:
        tr = MonsterTranslation(
            monster_id=monster_id,
            lang=lang,
            name=body.name,
            description=body.description,
        )
        session.add(tr)
    else:
        existing.name = body.name
        existing.description = body.description
        session.add(existing)

    session.commit()
    logger.info(
        "Monster translation upserted",
        extra={"monster_id": monster_id, "lang": lang.value},
    )
    return None


# ---------------------------- Wrapped responses ----------------------------


def _effective_monster_translation_dict(
    session: Session, monster_id: int, lang: Optional[str]
) -> Optional[Dict[str, Any]]:
    primary = _select_language(lang)
    fallback = _fallback_language(primary)
    tr = session.exec(
        select(MonsterTranslation).where(
            MonsterTranslation.monster_id == monster_id,
            MonsterTranslation.lang == primary,
        )
    ).first()
    if tr is None:
        tr = session.exec(
            select(MonsterTranslation).where(
                MonsterTranslation.monster_id == monster_id,
                MonsterTranslation.lang == fallback,
            )
        ).first()
    if tr is None:
        return None
    # Convert to plain dict, exclude None values for compactness
    data = tr.model_dump()
    # Drop identifiers and timestamps that are not needed by bot
    for k in ("id", "monster_id", "created_at", "updated_at"):
        data.pop(k, None)
    return data


def _labels_for_monster(
    labels: Dict[tuple[str, str], str], m: Monster
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if m.type:
        code = str(m.type).lower()
        out["type"] = {"code": code, "label": labels.get(("monster_type", code), code)}
    if m.size:
        code = str(m.size).lower()
        out["size"] = {"code": code, "label": labels.get(("monster_size", code), code)}
    if m.cr:
        code = str(m.cr)
        out["cr"] = {"code": code, "label": labels.get(("danger_level", code), code)}
    return out


@router.get("/wrapped-list", response_model=List[Dict[str, Any]])
def list_monsters_wrapped(
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Dict[str, Any]]:
    monsters = session.exec(select(Monster)).all()
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    # Resolve labels in bulk
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
                "translation": _effective_monster_translation_dict(session, int(m.id), lang)
                if m.id is not None
                else None,
                "labels": _labels_for_monster(labels, m),
            }
        )
    logger.info("Monsters wrapped listed", extra={"count": len(result)})
    return result


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
        "labels": _labels_for_monster(labels, m),
    }
    logger.info("Monster wrapped fetched", extra={"monster_id": monster_id})
    return body


