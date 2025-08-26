from enum import Enum


class DangerLevel(str, Enum):
    """Threat level for monsters."""

    TRIVIAL = "trivial"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    DEADLY = "deadly"


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


