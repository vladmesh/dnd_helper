from typing import Any, Dict, List, Optional

from sqlalchemy import SmallInteger, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field

from .base import BaseModel
from .enums import DangerLevel


class Monster(BaseModel, table=True):
    """Monster shared model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    # Iteration 3: `cr` replaces dangerous_lvl and becomes enum-string
    hp: int
    ac: int
    
    # Iteration 2: expose optional fields for API acceptance/return (DB columns already exist)
    type: Optional[str] = Field(default=None, index=True)
    size: Optional[str] = Field(default=None, index=True)
    alignment: Optional[str] = Field(default=None)
    hit_dice: Optional[str] = Field(default=None)
    cr: Optional[DangerLevel] = Field(default=None, sa_type=String(), index=True)
    xp: Optional[int] = Field(default=None)
    proficiency_bonus: Optional[int] = Field(default=None)
    abilities: Optional[Dict[str, int]] = Field(default=None, sa_type=JSONB)
    saving_throws: Optional[Dict[str, int]] = Field(default=None, sa_type=JSONB)
    skills: Optional[Dict[str, int]] = Field(default=None, sa_type=JSONB)
    senses: Optional[Dict[str, int]] = Field(default=None, sa_type=JSONB)
    languages: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()))
    damage_immunities: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()))
    damage_resistances: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()))
    damage_vulnerabilities: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()))
    condition_immunities: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()))
    tags: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()))

    # Iteration 1 — additive fields (nullable; keep legacy speed intact)
    # Localization
    slug: Optional[str] = Field(default=None, index=True)

    # Taxonomy and context
    subtypes: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()), index=True)
    environments: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()), index=True)
    roles: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()), index=True)

    # Flags and meta
    is_legendary: Optional[bool] = Field(default=None, index=True)
    has_lair_actions: Optional[bool] = Field(default=None, index=True)
    is_spellcaster: Optional[bool] = Field(default=None, index=True)
    source: Optional[str] = Field(default=None, index=True)
    page: Optional[int] = Field(default=None)

    # Derived fast flags
    is_flying: Optional[bool] = Field(default=None, index=True)
    has_ranged: Optional[bool] = Field(default=None, index=True)
    has_aoe: Optional[bool] = Field(default=None, index=True)

    # Speeds derived
    speed_walk: Optional[int] = Field(default=None, index=True)
    speed_fly: Optional[int] = Field(default=None, index=True)
    speed_swim: Optional[int] = Field(default=None, index=True)
    speed_climb: Optional[int] = Field(default=None, index=True)
    speed_burrow: Optional[int] = Field(default=None, index=True)

    # Senses derived
    has_darkvision: Optional[bool] = Field(default=None, index=True)
    darkvision_range: Optional[int] = Field(default=None)
    has_blindsight: Optional[bool] = Field(default=None, index=True)
    blindsight_range: Optional[int] = Field(default=None)
    has_truesight: Optional[bool] = Field(default=None, index=True)
    truesight_range: Optional[int] = Field(default=None)
    tremorsense_range: Optional[int] = Field(default=None, index=True)


