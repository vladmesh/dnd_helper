from __future__ import annotations

from typing import Dict, Iterable, Mapping, Set, Tuple

from sqlmodel import Session, select

from shared_models.enum_translation import EnumTranslation
from shared_models.enums import Language


def resolve_enum_labels(
    session: Session,
    requested_lang: Language,
    codes_by_type: Mapping[str, Set[str]],
) -> Dict[Tuple[str, str], str]:
    """
    Resolve localized labels for given enum codes.

    Returns mapping {(enum_type, enum_value) -> label} using requested language
    with fallback to the opposite language if a specific pair is missing.
    """
    result: Dict[Tuple[str, str], str] = {}
    if not codes_by_type:
        return result

    # Flatten requested pairs
    requested_pairs: Set[Tuple[str, str]] = set()
    for enum_type, values in codes_by_type.items():
        for value in values:
            requested_pairs.add((enum_type, value))

    # Helper to bulk fetch for a language
    def _fetch(lang: Language) -> Dict[Tuple[str, str], str]:
        rows = session.exec(
            select(EnumTranslation).where(
                EnumTranslation.lang == lang,
                EnumTranslation.enum_type.in_(list(codes_by_type.keys())),
                EnumTranslation.enum_value.in_(
                    list({v for values in codes_by_type.values() for v in values})
                ),
            )
        ).all()
        return {(r.enum_type, r.enum_value): r.label for r in rows}

    primary = _fetch(requested_lang)
    result.update(primary)

    # Fallback for missing pairs
    if len(result) < len(requested_pairs):
        fallback_lang = Language.EN if requested_lang == Language.RU else Language.RU
        fallback = _fetch(fallback_lang)
        for pair in requested_pairs:
            if pair not in result and pair in fallback:
                result[pair] = fallback[pair]

    return result


