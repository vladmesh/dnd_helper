from enum import Enum


class CasterClass(str, Enum):
    """Caster class enum for spells."""

    WIZARD = "wizard"
    SORCERER = "sorcerer"
    CLERIC = "cleric"
    DRUID = "druid"
    PALADIN = "paladin"
    RANGER = "ranger"
    BARD = "bard"
    WARLOCK = "warlock"


class SpellSchool(str, Enum):
    """Spell schools enum."""

    ABJURATION = "abjuration"
    CONJURATION = "conjuration"
    DIVINATION = "divination"
    ENCHANTMENT = "enchantment"
    EVOCATION = "evocation"
    ILLUSION = "illusion"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"


class Targeting(str, Enum):
    SELF = "self"
    CREATURE = "creature"
    CREATURES = "creatures"
    OBJECT = "object"
    POINT = "point"


class AreaShape(str, Enum):
    LINE = "line"
    CONE = "cone"
    CUBE = "cube"
    SPHERE = "sphere"
    CYLINDER = "cylinder"


class CastingTimeNormalized(str, Enum):
    ACTION = "action"
    BONUS_ACTION = "bonus_action"
    REACTION = "reaction"
    MINUTE_1 = "1m"
    MINUTE_10 = "10m"
    HOUR_1 = "1h"
    HOUR_8 = "8h"


