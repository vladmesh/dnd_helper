from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from shared_models import Monster
from shared_models.enums import Language
from shared_models.monster_translation import MonsterTranslation


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


def _apply_monster_translation(session: Session, monster: Monster, lang: Optional[str]) -> None:
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


def _apply_monster_translations_bulk(session: Session, monsters: List[Monster], lang: Optional[str]) -> None:
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


def _effective_monster_translation_dict(session: Session, monster_id: int, lang: Optional[str]) -> Optional[Dict[str, Any]]:
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
    data = tr.model_dump()
    for k in ("id", "monster_id", "created_at", "updated_at"):
        data.pop(k, None)
    return data


