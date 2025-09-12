from enum import Enum


class DangerLevel(str, Enum):
    """Challenge Rating values for monsters (final)."""

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



