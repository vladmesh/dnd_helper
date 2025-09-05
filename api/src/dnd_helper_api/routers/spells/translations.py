from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from shared_models import Spell
from shared_models.enums import Language
from shared_models.spell_translation import SpellTranslation


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


def _apply_spell_translation(session: Session, spell: Spell, lang: Optional[str]) -> None:
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


def _apply_spell_translations_bulk(session: Session, spells: List[Spell], lang: Optional[str]) -> None:
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


def _effective_spell_translation_dict(session: Session, spell_id: int, lang: Optional[str]) -> Optional[Dict[str, Any]]:
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


