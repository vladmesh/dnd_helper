from typing import Any, Optional

from shared_models import Monster


def _compute_monster_derived_fields(monster: Monster) -> None:
    senses: dict[str, Any] = monster.senses or {}

    def _as_int(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    if monster.speed_fly is not None:
        monster.is_flying = monster.speed_fly > 0

    def _sense_pair(key: str) -> tuple[Optional[bool], Optional[int]]:
        rng = _as_int(senses.get(key)) if key in senses else None
        flag = (rng is not None and rng > 0) if key in senses else None
        return flag, rng

    has_darkvision, darkvision_range = _sense_pair("darkvision")
    has_blindsight, blindsight_range = _sense_pair("blindsight")
    has_truesight, truesight_range = _sense_pair("truesight")
    tremorsense_range = _as_int(senses.get("tremorsense")) if "tremorsense" in senses else None

    monster.has_darkvision = has_darkvision
    monster.darkvision_range = darkvision_range
    monster.has_blindsight = has_blindsight
    monster.blindsight_range = blindsight_range
    monster.has_truesight = has_truesight
    monster.truesight_range = truesight_range
    monster.tremorsense_range = tremorsense_range


def _slugify(value: str) -> str:
    text = value.strip().lower()
    import re
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


