from typing import Any, Dict, List, Optional, Tuple

from telegram.ext import ContextTypes


def _default_monsters_filters() -> Dict[str, Any]:
    return {
        "legendary": None,  # None or True
        "flying": None,  # None or True
        "cr_range": None,  # "03" | "48" | "9p" | None
        "size": None,  # "S" | "M" | "L" | None
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
    # token formats: leg | fly | cr:03|48|9p | sz:S|M|L
    updated = dict(pending)
    if token == "leg":
        updated["legendary"] = None if pending.get("legendary") else True
    elif token == "fly":
        updated["flying"] = None if pending.get("flying") else True
    elif token.startswith("cr:"):
        val = token.split(":", 1)[1]
        updated["cr_range"] = None if pending.get("cr_range") == val else val
    elif token.startswith("sz:"):
        val = token.split(":", 1)[1]
        updated["size"] = None if pending.get("size") == val else val
    return updated


def _filter_monsters(items: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    def cr_in_range(cr_value: Optional[float], rng: Optional[str]) -> bool:
        if rng is None:
            return True
        if cr_value is None:
            return False
        if rng == "03":
            return 0 <= cr_value <= 3
        if rng == "48":
            return 4 <= cr_value <= 8
        if rng == "9p":
            return cr_value >= 9
        return True

    result: List[Dict[str, Any]] = []
    for m in items:
        if filters.get("legendary") is True and not m.get("is_legendary", False):
            continue
        if filters.get("flying") is True and not m.get("is_flying", False):
            continue
        if not cr_in_range(m.get("cr"), filters.get("cr_range")):
            continue
        size = filters.get("size")
        if size is not None and m.get("size") != size:
            continue
        result.append(m)
    return result


