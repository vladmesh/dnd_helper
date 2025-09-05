from enum import Enum


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


class Language(str, Enum):
    RU = "ru"
    EN = "en"


