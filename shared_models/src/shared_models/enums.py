from enum import Enum


class DangerLevel(str, Enum):
    """Threat level for monsters."""

    TRIVIAL = "trivial"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    DEADLY = "deadly"


class ChallengeRating(str, Enum):
    """CR domain values for monsters (temporary for Iteration 1)."""

    CR_1_8 = "1/8"
    CR_1_4 = "1/4"
    CR_1_2 = "1/2"
    CR_1 = "1"
    CR_2 = "2"
    CR_3 = "3"
    CR_4 = "4"
    CR_5 = "5"
    CR_6 = "6"
    CR_7 = "7"
    CR_8 = "8"
    CR_9 = "9"
    CR_10 = "10"
    CR_11 = "11"
    CR_12 = "12"
    CR_13 = "13"
    CR_14 = "14"
    CR_15 = "15"
    CR_16 = "16"
    CR_17 = "17"
    CR_18 = "18"
    CR_19 = "19"
    CR_20 = "20"
    CR_21 = "21"
    CR_22 = "22"
    CR_23 = "23"
    CR_24 = "24"
    CR_25 = "25"
    CR_26 = "26"
    CR_27 = "27"
    CR_28 = "28"
    CR_29 = "29"
    CR_30 = "30"


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

