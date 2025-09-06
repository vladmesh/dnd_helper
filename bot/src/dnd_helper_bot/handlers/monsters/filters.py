from typing import Any, Dict, List, Optional, Tuple, Set

from telegram.ext import ContextTypes


def _default_monsters_filters() -> Dict[str, Any]:
    return {
        "legendary": None,  # kept for future iterations; None or True/False
        "flying": None,  # kept for future iterations; None or True/False
        # Iteration 1 fields
        "cr_buckets": None,  # None or set({"03","48","9p"})
        "types": None,  # None or set of type codes (strings)
        # Legacy fields (kept for compatibility; not used in Iteration 1 UI)
        "cr_range": None,  # legacy single bucket
        "size": None,  # legacy single size code
    }


def _get_filter_state(context: ContextTypes.DEFAULT_TYPE) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    user_data = context.user_data
    if "monsters_filters_pending" not in user_data:
        user_data["monsters_filters_pending"] = _default_monsters_filters()
    if "monsters_filters_applied" not in user_data:
        user_data["monsters_filters_applied"] = _default_monsters_filters()
    return user_data["monsters_filters_pending"], user_data["monsters_filters_applied"]


def _set_filter_state(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    pending: Optional[Dict[str, Any]] = None,
    applied: Optional[Dict[str, Any]] = None,
) -> None:
    if pending is not None:
        context.user_data["monsters_filters_pending"] = pending
    if applied is not None:
        context.user_data["monsters_filters_applied"] = applied


def _toggle_or_set_filters(pending: Dict[str, Any], token: str) -> Dict[str, Any]:
    # token formats:
    #  - cr:any | cr:03|48|9p
    #  - type:any | type:<code>
    #  - legacy still supported: leg | fly | sz:S|M|L
    updated = dict(pending)

    # CR buckets (multi-select)
    if token.startswith("cr:"):
        val = token.split(":", 1)[1]
        if val == "any":
            updated["cr_buckets"] = None
            # keep legacy empty
            updated["cr_range"] = None
        else:
            current: Optional[Set[str]] = updated.get("cr_buckets")
            current_set: Set[str] = set(current) if isinstance(current, set) else set()
            if val in current_set:
                current_set.remove(val)
            else:
                current_set.add(val)
            updated["cr_buckets"] = current_set or None
            # keep legacy empty
            updated["cr_range"] = None
        return updated

    # Types (multi-select)
    if token.startswith("type:"):
        val = token.split(":", 1)[1]
        if val == "any":
            updated["types"] = None
        else:
            current: Optional[Set[str]] = updated.get("types")
            current_set: Set[str] = set(current) if isinstance(current, set) else set()
            if val in current_set:
                current_set.remove(val)
            else:
                current_set.add(val)
            updated["types"] = current_set or None
        return updated

    # Legacy/other toggles (kept for compatibility; not in Iteration 1 UI)
    if token == "leg":
        updated["legendary"] = None if pending.get("legendary") else True
        return updated
    if token == "fly":
        updated["flying"] = None if pending.get("flying") else True
        return updated
    if token.startswith("sz:"):
        val = token.split(":", 1)[1]
        updated["size"] = None if pending.get("size") == val else val
        return updated

    return updated


def _filter_monsters(items: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    def cr_bucket_match(cr_value: Optional[float], buckets: Optional[Set[str]], legacy: Optional[str]) -> bool:
        if buckets is None and legacy is None:
            return True
        if cr_value is None:
            return False
        # If new buckets are present, use OR across them
        targets: List[str]
        if isinstance(buckets, set) and buckets:
            targets = list(buckets)
        elif isinstance(legacy, str) and legacy:
            targets = [legacy]
        else:
            return True
        for rng in targets:
            if rng == "03" and 0 <= cr_value <= 3:
                return True
            if rng == "48" and 4 <= cr_value <= 8:
                return True
            if rng == "9p" and cr_value >= 9:
                return True
        return False

    result: List[Dict[str, Any]] = []
    selected_types: Optional[Set[str]] = filters.get("types") if isinstance(filters.get("types"), set) else None
    for m in items:
        # Booleans (kept simple for Iteration 1)
        if filters.get("legendary") is True and not m.get("is_legendary", False):
            continue
        if filters.get("flying") is True and not m.get("is_flying", False):
            continue
        # CR buckets
        if not cr_bucket_match(m.get("cr"), filters.get("cr_buckets"), filters.get("cr_range")):
            continue
        # Size (legacy)
        size = filters.get("size")
        if size is not None and m.get("size") != size:
            continue
        # Types (multi-select OR)
        if selected_types is not None:
            # Monsters list does not currently include normalized type in the derived dict; skip until available
            # Type filtering will be applied at render step if types are included
            m_type: Optional[str] = m.get("type")
            if m_type is None or m_type not in selected_types:
                continue
        result.append(m)
    return result


