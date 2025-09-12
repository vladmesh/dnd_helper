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



def _slugify(value: str) -> str:
    text = value.strip().lower()
    import re
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


