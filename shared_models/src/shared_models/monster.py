from typing import Dict, List, Optional, Any

from pydantic import ConfigDict, field_validator
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field

from .base import BaseModel
from .enums import DangerLevel, Ability, Skill


class Monster(BaseModel, table=True):
    """Monster shared model."""

    model_config = ConfigDict(extra="forbid")

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
    ability_scores: Optional[Dict[str, int]] = Field(default=None, sa_type=JSONB)
    saving_throws: Optional[Dict[str, int]] = Field(default=None, sa_type=JSONB)
    skills: Optional[Dict[str, int]] = Field(default=None, sa_type=JSONB)
    senses: Optional[Dict[str, int]] = Field(default=None, sa_type=JSONB)
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

    # Speeds derived
    speed_walk: Optional[int] = Field(default=None, index=True)
    speed_fly: Optional[int] = Field(default=None, index=True)
    speed_swim: Optional[int] = Field(default=None, index=True)
    speed_climb: Optional[int] = Field(default=None, index=True)
    speed_burrow: Optional[int] = Field(default=None, index=True)

    @field_validator("ability_scores", mode="before")
    @classmethod
    def _validate_ability_scores(cls, value: Any) -> Any:
        if value is None:
            return value
        if not isinstance(value, dict):
            raise ValueError("ability_scores must be a dict")
        valid = {a.value for a in Ability}
        for k, v in value.items():
            if k not in valid:
                raise ValueError(f"Invalid ability key: {k}")
            if not isinstance(v, int):
                raise ValueError(f"Invalid ability value for {k}: must be int")
        return value

    @field_validator("saving_throws", mode="before")
    @classmethod
    def _validate_saving_throws(cls, value: Any) -> Any:
        if value is None:
            return value
        if not isinstance(value, dict):
            raise ValueError("saving_throws must be a dict")
        valid = {a.value for a in Ability}
        for k, v in value.items():
            if k not in valid:
                raise ValueError(f"Invalid saving throw key: {k}")
            if not isinstance(v, int):
                raise ValueError(f"Invalid saving throw value for {k}: must be int")
        return value

    @field_validator("skills", mode="before")
    @classmethod
    def _validate_skills(cls, value: Any) -> Any:
        if value is None:
            return value
        if not isinstance(value, dict):
            raise ValueError("skills must be a dict")
        valid = {s.value for s in Skill}
        for k, v in value.items():
            if k not in valid:
                raise ValueError(f"Invalid skill key: {k}")
            if not isinstance(v, int):
                raise ValueError(f"Invalid skill value for {k}: must be int")
        return value



