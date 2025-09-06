from typing import Any, Dict, List, Optional, Tuple, Set

from telegram.ext import ContextTypes


def _default_monsters_filters() -> Dict[str, Any]:
    return {
        "legendary": None,  # kept for future iterations; None or True/False
        "flying": None,  # kept for future iterations; None or True/False
        # Iteration 1 fields
        "cr_buckets": None,  # None or set({"03","48","9p"})
        "types": None,  # None or set of type codes (strings)
        "sizes": None,  # None or set of size codes (e.g., {"S","M","L"})
        # UI ordering of visible filter rows
        "visible_fields": ["cr_buckets", "types"],
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
    # Backfill newly introduced keys if missing
    for key in ("cr_buckets", "types", "sizes", "visible_fields"):
        if key not in user_data["monsters_filters_pending"]:
            user_data["monsters_filters_pending"][key] = _default_monsters_filters()[key]
        if key not in user_data["monsters_filters_applied"]:
            user_data["monsters_filters_applied"][key] = _default_monsters_filters()[key]
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
    #  - sz:any | sz:S|M|L
    #  - fly:any|yes|no, leg:any|yes|no
    #  - add, add:<field>, rm:<field>
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

    # Sizes (multi-select)
    if token.startswith("sz:"):
        val = token.split(":", 1)[1]
        if val == "any":
            updated["sizes"] = None
            # legacy
            updated["size"] = None
        else:
            current: Optional[Set[str]] = updated.get("sizes")
            current_set: Set[str] = set(current) if isinstance(current, set) else set()
            if val in current_set:
                current_set.remove(val)
            else:
                current_set.add(val)
            updated["sizes"] = current_set or None
            updated["size"] = None
        return updated

    # Booleans (tri-state via any/yes/no)
    if token.startswith("fly:"):
        val = token.split(":", 1)[1]
        updated["flying"] = None if val == "any" else (True if val == "yes" else False)
        return updated
    if token.startswith("leg:"):
        val = token.split(":", 1)[1]
        updated["legendary"] = None if val == "any" else (True if val == "yes" else False)
        return updated

    # Manage visible fields
    if token.startswith("add:"):
        field = token.split(":", 1)[1]
        vf: List[str] = list(updated.get("visible_fields") or [])
        if field and field not in vf:
            vf.append(field)
        updated["visible_fields"] = vf
        # Ensure field value is Any for a newly added filter
        if field in ("cr_buckets", "types", "sizes"):
            updated[field] = None
        if field in ("flying", "legendary"):
            updated[field] = None
        return updated
    if token.startswith("rm:"):
        field = token.split(":", 1)[1]
        vf: List[str] = list(updated.get("visible_fields") or [])
        if field in vf:
            vf.remove(field)
        updated["visible_fields"] = vf
        # Clear field value on remove
        if field in ("cr_buckets", "types", "sizes", "cr_range", "size"):
            updated[field] = None
        if field in ("flying", "legendary"):
            updated[field] = None
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
    selected_sizes: Optional[Set[str]] = filters.get("sizes") if isinstance(filters.get("sizes"), set) else None
    for m in items:
        # Booleans (tri-state)
        leg = filters.get("legendary")
        if leg is True and not m.get("is_legendary", False):
            continue
        if leg is False and m.get("is_legendary", False):
            continue
        fly = filters.get("flying")
        if fly is True and not m.get("is_flying", False):
            continue
        if fly is False and m.get("is_flying", False):
            continue
        # CR buckets
        if not cr_bucket_match(m.get("cr"), filters.get("cr_buckets"), filters.get("cr_range")):
            continue
        # Size (multi-select OR); fallback to legacy single
        if selected_sizes is not None:
            if m.get("size") not in selected_sizes:
                continue
        else:
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


