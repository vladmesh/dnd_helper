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


# Iteration 0 — Enums and groundwork
class MovementMode(str, Enum):
    WALK = "walk"
    FLY = "fly"
    SWIM = "swim"
    CLIMB = "climb"
    BURROW = "burrow"


class SpellComponent(str, Enum):
    V = "v"
    S = "s"
    M = "m"


class Environment(str, Enum):
    ARCTIC = "arctic"
    DESERT = "desert"
    FOREST = "forest"
    GRASSLAND = "grassland"
    MOUNTAIN = "mountain"
    SWAMP = "swamp"
    COAST = "coast"
    UNDERDARK = "underdark"
    URBAN = "urban"
    PLANAR = "planar"


class MonsterSize(str, Enum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"


class MonsterType(str, Enum):
    ABERRATION = "aberration"
    BEAST = "beast"
    CELESTIAL = "celestial"
    CONSTRUCT = "construct"
    DRAGON = "dragon"
    ELEMENTAL = "elemental"
    FEY = "fey"
    FIEND = "fiend"
    GIANT = "giant"
    HUMANOID = "humanoid"
    MONSTROSITY = "monstrosity"
    OOZE = "ooze"
    PLANT = "plant"
    UNDEAD = "undead"


class Ability(str, Enum):
    STR = "str"
    DEX = "dex"
    CON = "con"
    INT = "int"
    WIS = "wis"
    CHA = "cha"


class DamageType(str, Enum):
    ACID = "acid"
    COLD = "cold"
    FIRE = "fire"
    FORCE = "force"
    LIGHTNING = "lightning"
    NECROTIC = "necrotic"
    POISON = "poison"
    PSYCHIC = "psychic"
    RADIANT = "radiant"
    THUNDER = "thunder"
    BLUDGEONING = "bludgeoning"
    PIERCING = "piercing"
    SLASHING = "slashing"


class Condition(str, Enum):
    BLINDED = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    PRONE = "prone"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"
    EXHAUSTION = "exhaustion"


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


class SaveEffect(str, Enum):
    HALF = "half"
    NEGATE = "negate"
    PARTIAL = "partial"


class MonsterRole(str, Enum):
    BRUTE = "brute"
    SKIRMISHER = "skirmisher"
    ARTILLERY = "artillery"
    CONTROLLER = "controller"
    LURKER = "lurker"
    SUPPORT = "support"
    SOLO = "solo"

