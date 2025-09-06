from typing import Any, Dict, List, Optional, Tuple

from telegram.ext import ContextTypes


def _default_spells_filters() -> Dict[str, Any]:
    return {
        "ritual": None,  # None or True
        "is_concentration": None,  # None or True
        "cast": {"bonus": False, "reaction": False},
        "level_range": None,  # "13" | "45" | "69" | None (legacy single-choice)
        # New set-based fields (Iteration 1)
        "level_buckets": None,  # set[str] | None
        "school": None,  # set[str] | None
        # Iteration 2 additions
        "casting_time": None,  # set[str] | None, values {"ba", "re"}
        "classes": None,  # set[str] | None
        # UI state for rendering
        "visible_fields": ["level_buckets", "school"],
        "add_menu_open": False,
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
    # Supported tokens:
    # rit | conc | rit:any|yes|no | conc:any|yes|no
    # ct:any | ct:ba | ct:re
    # lv:any | lv:13 | lv:45 | lv:69
    # sc:any | sc:<code>
    # cls:any | cls:<code>
    # add | add:<field> | rm:<field>
    updated = {**pending, "cast": {**pending.get("cast", {})}}
    if token == "rit":
        updated["ritual"] = None if pending.get("ritual") else True
    elif token == "conc":
        updated["is_concentration"] = None if pending.get("is_concentration") else True
    elif token.startswith("rit:"):
        val = token.split(":", 1)[1]
        if val == "any":
            updated["ritual"] = None
        elif val == "yes":
            updated["ritual"] = True
        elif val == "no":
            updated["ritual"] = False
    elif token.startswith("conc:"):
        val = token.split(":", 1)[1]
        if val == "any":
            updated["is_concentration"] = None
        elif val == "yes":
            updated["is_concentration"] = True
        elif val == "no":
            updated["is_concentration"] = False
    elif token.startswith("ct:"):
        val = token.split(":", 1)[1]
        if val == "any":
            updated["casting_time"] = None
            # mirror legacy
            updated["cast"]["bonus"] = False
            updated["cast"]["reaction"] = False
        else:
            current = set(updated.get("casting_time") or [])
            if val in current:
                current.remove(val)
            else:
                current.add(val)
            updated["casting_time"] = current if current else None
            # mirror legacy flags
            updated["cast"]["bonus"] = "ba" in (updated["casting_time"] or set())
            updated["cast"]["reaction"] = "re" in (updated["casting_time"] or set())
    elif token.startswith("lv:"):
        val = token.split(":", 1)[1]
        if val == "any":
            updated["level_buckets"] = None
            updated["level_range"] = None
        else:
            current = set(updated.get("level_buckets") or [])
            if val in current:
                current.remove(val)
            else:
                current.add(val)
            updated["level_buckets"] = current if current else None
            # clear legacy single-range when multi-select used
            updated["level_range"] = None
    elif token.startswith("sc:"):
        val = token.split(":", 1)[1]
        if val == "any":
            updated["school"] = None
        else:
            current = set(updated.get("school") or [])
            if val in current:
                current.remove(val)
            else:
                current.add(val)
            updated["school"] = current if current else None
    elif token.startswith("cls:"):
        val = token.split(":", 1)[1]
        if val == "any":
            updated["classes"] = None
        else:
            current = set(updated.get("classes") or [])
            if val in current:
                current.remove(val)
            else:
                current.add(val)
            updated["classes"] = current if current else None
    elif token == "add":
        updated["add_menu_open"] = True
    elif token.startswith("add:"):
        field = token.split(":", 1)[1]
        vf = list(updated.get("visible_fields") or [])
        if field not in vf:
            vf.append(field)
        updated["visible_fields"] = vf
        updated["add_menu_open"] = False
        # clear the field value to Any
        if field in ("level_buckets", "school", "casting_time", "classes"):
            updated[field] = None
        elif field in ("ritual", "is_concentration"):
            updated[field] = None
    elif token.startswith("rm:"):
        field = token.split(":", 1)[1]
        vf = [f for f in (updated.get("visible_fields") or []) if f != field]
        updated["visible_fields"] = vf
        # clear value when removing
        if field in updated:
            updated[field] = None
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

    def level_in_bucket(level: Optional[int], bucket: str) -> bool:
        if level is None:
            return False
        if bucket == "13":
            return 1 <= level <= 3
        if bucket == "45":
            return 4 <= level <= 5
        if bucket == "69":
            return 6 <= level <= 9
        return False

    result: List[Dict[str, Any]] = []
    for s in items:
        if filters.get("ritual") is True and not s.get("ritual", False):
            continue
        if filters.get("is_concentration") is True and not s.get("is_concentration", False):
            continue
        # Casting time: prefer new set-based field, fallback to legacy booleans
        ct_set = filters.get("casting_time")
        legacy_cast = filters.get("cast", {})
        want_bonus = (ct_set is not None and "ba" in ct_set) or (ct_set is None and legacy_cast.get("bonus", False))
        want_react = (ct_set is not None and "re" in ct_set) or (ct_set is None and legacy_cast.get("reaction", False))
        if not match_casting_time(s.get("casting_time"), want_bonus, want_react):
            continue
        # Level: new set-based field preferred; fallback to legacy single-range
        level_buckets = filters.get("level_buckets")
        if level_buckets:
            if not any(level_in_bucket(s.get("level"), b) for b in level_buckets):
                continue
        else:
            legacy = filters.get("level_range")
            if legacy is not None and not level_in_bucket(s.get("level"), legacy):
                continue
        # School: OR within field
        school_selected = filters.get("school")
        if school_selected:
            scode = s.get("school")
            if scode is None or scode not in school_selected:
                continue
        # Classes: intersection non-empty
        classes_selected = filters.get("classes")
        if classes_selected:
            spell_classes = set(s.get("classes") or [])
            if not (spell_classes & set(classes_selected)):
                continue
        result.append(s)
    return result


