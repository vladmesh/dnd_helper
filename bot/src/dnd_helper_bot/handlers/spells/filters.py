from typing import Any, Dict, List, Optional, Tuple

from telegram.ext import ContextTypes


def _default_spells_filters() -> Dict[str, Any]:
    return {
        "ritual": None,  # None or True
        "is_concentration": None,  # None or True
        "cast": {"bonus": False, "reaction": False},
        "level_range": None,  # "13" | "45" | "69" | None
    }


def _get_filter_state(context: ContextTypes.DEFAULT_TYPE) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    user_data = context.user_data
    if "spells_filters_pending" not in user_data:
        user_data["spells_filters_pending"] = _default_spells_filters()
    if "spells_filters_applied" not in user_data:
        user_data["spells_filters_applied"] = _default_spells_filters()
    return user_data["spells_filters_pending"], user_data["spells_filters_applied"]


def _set_filter_state(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    pending: Optional[Dict[str, Any]] = None,
    applied: Optional[Dict[str, Any]] = None,
) -> None:
    if pending is not None:
        context.user_data["spells_filters_pending"] = pending
    if applied is not None:
        context.user_data["spells_filters_applied"] = applied


def _toggle_or_set_filters(pending: Dict[str, Any], token: str) -> Dict[str, Any]:
    # token formats: rit | conc | ct:ba | ct:re | lv:13 | lv:45 | lv:69
    updated = {**pending, "cast": {**pending.get("cast", {})}}
    if token == "rit":
        updated["ritual"] = None if pending.get("ritual") else True
    elif token == "conc":
        updated["is_concentration"] = None if pending.get("is_concentration") else True
    elif token == "ct:ba":
        updated["cast"]["bonus"] = not pending.get("cast", {}).get("bonus", False)
    elif token == "ct:re":
        updated["cast"]["reaction"] = not pending.get("cast", {}).get("reaction", False)
    elif token.startswith("lv:"):
        val = token.split(":", 1)[1]
        updated["level_range"] = None if pending.get("level_range") == val else val
    return updated


def _filter_spells(items: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    def match_casting_time(value: Optional[str], want_bonus: bool, want_reaction: bool) -> bool:
        if not (want_bonus or want_reaction):
            return True
        if value is None:
            return False
        v = str(value).lower()
        bonus_ok = ("bonus_action" in v) or ("bonus action" in v)
        react_ok = "reaction" in v
        conds: List[bool] = []
        if want_bonus:
            conds.append(bonus_ok)
        if want_reaction:
            conds.append(react_ok)
        return all(conds)

    def level_in_range(level: Optional[int], rng: Optional[str]) -> bool:
        if rng is None:
            return True
        if level is None:
            return False
        if rng == "13":
            return 1 <= level <= 3
        if rng == "45":
            return 4 <= level <= 5
        if rng == "69":
            return 6 <= level <= 9
        return True

    result: List[Dict[str, Any]] = []
    for s in items:
        if filters.get("ritual") is True and not s.get("ritual", False):
            continue
        if filters.get("is_concentration") is True and not s.get("is_concentration", False):
            continue
        cast = filters.get("cast", {})
        if not match_casting_time(s.get("casting_time"), cast.get("bonus", False), cast.get("reaction", False)):
            continue
        if not level_in_range(s.get("level"), filters.get("level_range")):
            continue
        result.append(s)
    return result


