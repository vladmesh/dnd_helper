from enum import Enum

from .enums_common import (
    Ability,
    Condition,
    DamageType,
    Environment,
    Language,
    MovementMode,
    SpellComponent,
    Skill,
)
from .enums_monsters import (
    DangerLevel,
    MonsterRole,
    MonsterSize,
    MonsterType,
)
from .enums_spells import (
    AreaShape,
    CasterClass,
    CastingTimeNormalized,
    SpellSchool,
    Targeting,
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
    "Skill",
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

