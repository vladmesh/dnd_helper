from enum import Enum

from .enums_common import (
    MovementMode,
    SpellComponent,
    Environment,
    Ability,
    DamageType,
    Condition,
    Language,
)
from .enums_monsters import (
    DangerLevel,
    MonsterSize,
    MonsterType,
    MonsterRole,
)
from .enums_spells import (
    CasterClass,
    SpellSchool,
    Targeting,
    AreaShape,
    CastingTimeNormalized,
)


class SaveEffect(str, Enum):
    HALF = "half"
    NEGATE = "negate"
    PARTIAL = "partial"


__all__ = [
    # common
    "MovementMode",
    "SpellComponent",
    "Environment",
    "Ability",
    "DamageType",
    "Condition",
    "Language",
    # monsters
    "DangerLevel",
    "MonsterSize",
    "MonsterType",
    "MonsterRole",
    # spells
    "CasterClass",
    "SpellSchool",
    "Targeting",
    "AreaShape",
    "CastingTimeNormalized",
    # local
    "SaveEffect",
]

