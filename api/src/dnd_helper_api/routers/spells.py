import logging
from typing import Any, Dict, List, Optional

from dnd_helper_api.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request, Response
from sqlalchemy import delete
from sqlmodel import Session, select

from shared_models import Spell
from shared_models.enums import Language
from shared_models.spell_translation import SpellTranslation
from pydantic import BaseModel
from dnd_helper_api.utils.enum_labels import resolve_enum_labels

router = APIRouter(prefix="/spells", tags=["spells"])
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


def _apply_spell_translation(
    session: Session,
    spell: Spell,
    lang: Optional[str],
) -> None:
    """Apply localized name/description to a Spell instance in-place with fallback."""
    primary = _select_language(lang)
    fallback = _fallback_language(primary)
    tr = session.exec(
        select(SpellTranslation).where(
            SpellTranslation.spell_id == spell.id,
            SpellTranslation.lang == primary,
        )
    ).first()
    if tr is None:
        tr = session.exec(
            select(SpellTranslation).where(
                SpellTranslation.spell_id == spell.id,
                SpellTranslation.lang == fallback,
            )
        ).first()
    if tr is not None:
        for attr, value in (("name", tr.name), ("description", tr.description)):
            try:
                setattr(spell, attr, value)  # type: ignore[attr-defined]
            except Exception:
                pass


def _apply_spell_translations_bulk(
    session: Session,
    spells: List[Spell],
    lang: Optional[str],
) -> None:
    if not spells:
        return
    primary = _select_language(lang)
    fallback = _fallback_language(primary)
    spell_ids = [s.id for s in spells if s.id is not None]
    if not spell_ids:
        return
    rows = session.exec(
        select(SpellTranslation).where(
            SpellTranslation.spell_id.in_(spell_ids),
            SpellTranslation.lang.in_([primary, fallback]),
        )
    ).all()
    by_spell: Dict[int, Dict[Language, SpellTranslation]] = {}
    for r in rows:
        by_spell.setdefault(r.spell_id, {})[r.lang] = r
    for s in spells:
        if s.id is None:
            continue
        lang_map = by_spell.get(s.id) or {}
        tr = lang_map.get(primary) or lang_map.get(fallback)
        if tr is None:
            continue
        for attr, value in (("name", tr.name), ("description", tr.description)):
            try:
                setattr(s, attr, value)  # type: ignore[attr-defined]
            except Exception:
                pass


def _compute_spell_derived_fields(spell: Spell) -> None:
    """Populate derived fast-filter fields for Spell based on simple heuristics.

    Keep logic minimal and defensive: only set flags when source data is present.
    """
    # slug generation from name if not provided
    # slug generation skipped; localized name not stored on base model

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
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Spell]:
    if not q:
        logger.warning("Empty spell search query")
        return []
    # Build conditions on base table
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
    # Match only translations in the requested language; no fallback for matching
    requested_lang = _select_language(lang)
    pattern = f"%{q.strip()}%"
    stmt = (
        select(Spell)
        .join(SpellTranslation, SpellTranslation.spell_id == Spell.id)
        .where(
            SpellTranslation.lang == requested_lang,
            SpellTranslation.name.ilike(pattern),
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


def _with_labels(spell: Spell, labels: Dict[tuple[str, str], str]) -> Dict[str, Any]:
    body = spell.model_dump()
    # Include translated fields applied in-place
    name = getattr(spell, "name", None)
    if name is not None:
        body["name"] = name
    description = getattr(spell, "description", None)
    if description is not None:
        body["description"] = description
    # single code -> {code,label}
    code = body.get("school")
    if code:
        body["school"] = {"code": code, "label": labels.get(("spell_school", str(code)), str(code))}
    # array of codes -> array of {code,label}
    classes = body.get("classes") or []
    body["classes"] = [
        {"code": c, "label": labels.get(("caster_class", str(c)), str(c))} for c in classes
    ]
    return body


@router.post("", response_model=Spell, status_code=status.HTTP_201_CREATED)
async def create_spell(
    spell: Spell,
    lang: Optional[str] = None,
    request: Request = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> Spell:
    spell.id = None
    _compute_spell_derived_fields(spell)
    session.add(spell)
    session.commit()
    session.refresh(spell)
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
                    select(SpellTranslation).where(
                        SpellTranslation.spell_id == spell.id,
                        SpellTranslation.lang == l,
                    )
                ).first()
                if existing is None:
                    session.add(
                        SpellTranslation(
                            spell_id=spell.id,
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

    logger.info("Spell created", extra={"spell_id": spell.id})
    return spell


@router.get("", response_model=List[Spell])
def list_spells(
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Spell]:
    spells = session.exec(select(Spell)).all()
    _apply_spell_translations_bulk(session, spells, lang)
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    logger.info("Spells listed", extra={"count": len(spells)})
    return spells


# @router.get("/labeled", response_model=List[Dict[str, Any]])
def list_spells_labeled(
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Dict[str, Any]]:
    spells = session.exec(select(Spell)).all()
    _apply_spell_translations_bulk(session, spells, lang)
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    codes = {
        "spell_school": {str(s.school) for s in spells if s.school},
        "caster_class": {c for s in spells for c in (s.classes or [])},
    }
    labels = resolve_enum_labels(session, requested_lang, codes)
    return [_with_labels(s, labels) for s in spells]


# @router.get("/{spell_id}", response_model=Spell)
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


# @router.get("/{spell_id}/labeled", response_model=Dict[str, Any])
def get_spell_labeled(
    spell_id: int,
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> Dict[str, Any]:
    spell = session.get(Spell, spell_id)
    if spell is None:
        logger.warning("Spell not found", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    _apply_spell_translation(session, spell, lang)
    requested_lang = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    codes = {
        "spell_school": {str(spell.school)} if spell.school else set(),
        "caster_class": set(spell.classes or []),
    }
    labels = resolve_enum_labels(session, requested_lang, codes)
    return _with_labels(spell, labels)


@router.put("/{spell_id}", response_model=Spell)
async def update_spell(
    spell_id: int,
    payload: Spell,
    lang: Optional[str] = None,
    request: Request = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> Spell:
    spell = session.get(Spell, spell_id)
    if spell is None:
        logger.warning("Spell not found for update", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    # name/description moved to translations; skip base assignment
    # caster_class deprecated; rely on `classes`
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
    # concentration deprecated; `is_concentration` is derived from `duration`
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
                    select(SpellTranslation).where(
                        SpellTranslation.spell_id == spell.id,
                        SpellTranslation.lang == l,
                    )
                ).first()
                if existing is None:
                    session.add(
                        SpellTranslation(
                            spell_id=spell.id,
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
    logger.info("Spell updated", extra={"spell_id": spell.id})
    return spell


@router.delete("/{spell_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spell(
    spell_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> None:
    spell = session.get(Spell, spell_id)
    if spell is None:
        logger.warning("Spell not found for delete", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    # Delete translations first to satisfy FK constraints
    session.exec(
        delete(SpellTranslation).where(SpellTranslation.spell_id == spell_id)
    )
    session.delete(spell)
    session.commit()
    logger.info("Spell deleted", extra={"spell_id": spell_id})
    return None


class SpellTranslationUpsert(BaseModel):
    lang: str
    name: str
    description: str


@router.post("/{spell_id}/translations", status_code=status.HTTP_204_NO_CONTENT)
def upsert_spell_translation(
    spell_id: int,
    body: SpellTranslationUpsert,
    session: Session = Depends(get_session),  # noqa: B008
) -> None:
    spell = session.get(Spell, spell_id)
    if spell is None:
        logger.warning("Spell not found for translation upsert", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")

    lang = _select_language(body.lang)

    existing = session.exec(
        select(SpellTranslation).where(
            SpellTranslation.spell_id == spell_id,
            SpellTranslation.lang == lang,
        )
    ).first()

    if existing is None:
        tr = SpellTranslation(
            spell_id=spell_id,
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
        "Spell translation upserted",
        extra={"spell_id": spell_id, "lang": lang.value},
    )
    return None


# ---------------------------- Wrapped responses ----------------------------


def _effective_spell_translation_dict(
    session: Session, spell_id: int, lang: Optional[str]
) -> Optional[Dict[str, Any]]:
    primary = _select_language(lang)
    fallback = _fallback_language(primary)
    tr = session.exec(
        select(SpellTranslation).where(
            SpellTranslation.spell_id == spell_id,
            SpellTranslation.lang == primary,
        )
    ).first()
    if tr is None:
        tr = session.exec(
            select(SpellTranslation).where(
                SpellTranslation.spell_id == spell_id,
                SpellTranslation.lang == fallback,
            )
        ).first()
    if tr is None:
        return None
    data = tr.model_dump()
    for k in ("id", "spell_id", "created_at", "updated_at"):
        data.pop(k, None)
    return data


def _labels_for_spell(labels: Dict[tuple[str, str], str], s: Spell) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if s.school:
        code = str(s.school)
        out["school"] = {"code": code, "label": labels.get(("spell_school", code), code)}
    if s.classes:
        out["classes"] = [
            {"code": c, "label": labels.get(("caster_class", str(c)), str(c))}
            for c in s.classes
        ]
    return out


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
                "translation": _effective_spell_translation_dict(session, int(s.id), lang)
                if s.id is not None
                else None,
                "labels": _labels_for_spell(labels, s),
            }
        )
    logger.info("Spells wrapped listed", extra={"count": len(result)})
    return result


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
        "labels": _labels_for_spell(labels, s),
    }
    logger.info("Spell wrapped fetched", extra={"spell_id": spell_id})
    return body


@router.get("/search-wrapped", response_model=List[Dict[str, Any]])
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
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> List[Dict[str, Any]]:
    if not q:
        logger.warning("Empty spell search (wrapped) query")
        return []

    # Base filters
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

    # Match only requested language for substring
    requested_lang = _select_language(lang)
    pattern = f"%{q.strip()}%"
    stmt = (
        select(Spell)
        .join(SpellTranslation, SpellTranslation.spell_id == Spell.id)
        .where(
            SpellTranslation.lang == requested_lang,
            SpellTranslation.name.ilike(pattern),
            *conditions,
        )
        .distinct()
    )
    spells = session.exec(stmt).all()

    # Labels resolution
    codes = {
        "spell_school": {str(s.school) for s in spells if s.school},
        "caster_class": {c for s in spells for c in (s.classes or [])},
    }
    labels = resolve_enum_labels(session, requested_lang, codes)

    # Build wrapped structure
    result: List[Dict[str, Any]] = []
    for s in spells:
        result.append(
            {
                "entity": s.model_dump(),
                "translation": _effective_spell_translation_dict(session, int(s.id), lang)
                if s.id is not None
                else None,
                "labels": _labels_for_spell(labels, s),
            }
        )
    if response is not None:
        response.headers["Content-Language"] = requested_lang.value
    logger.info("Spells search-wrapped completed", extra={"query": q, "count": len(result)})
    return result


