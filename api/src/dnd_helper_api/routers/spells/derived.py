from typing import Any, Dict

from shared_models import Spell


def _normalize_casting_time(value: str) -> str:
    v = value.strip().lower()
    if "bonus action" in v:
        return "bonus_action"
    if "reaction" in v:
        return "reaction"
    if v == "action" or "1 action" in v:
        return "action"
    if "10 minute" in v or "10 min" in v or v.startswith("10m"):
        return "10m"
    if "1 minute" in v or "1 min" in v or v.startswith("1m"):
        return "1m"
    if "8 hour" in v or v.startswith("8h"):
        return "8h"
    if "1 hour" in v or v.startswith("1h"):
        return "1h"
    return v


def _compute_spell_derived_fields(spell: Spell) -> None:
    if spell.duration is not None:
        dur = str(spell.duration).lower()
        spell.is_concentration = ("concentration" in dur)

    damage: Dict[str, Any] = spell.damage or {}
    if isinstance(damage, dict) and damage.get("type") is not None:
        spell.damage_type = str(damage.get("type"))

    saving_throw: Dict[str, Any] = spell.saving_throw or {}
    if isinstance(saving_throw, dict) and saving_throw.get("ability") is not None:
        spell.save_ability = str(saving_throw.get("ability"))

    if spell.attack_roll is None:
        if damage and not saving_throw.get("ability"):
            spell.attack_roll = True

    if spell.targeting is None:
        area = spell.area or {}
        if area:
            spell.targeting = "POINT"

    if spell.casting_time is not None:
        spell.casting_time = _normalize_casting_time(str(spell.casting_time))


