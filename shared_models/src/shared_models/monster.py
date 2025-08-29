from typing import Any, Dict, List, Optional

from sqlmodel import Field
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from .base import BaseModel
from .enums import DangerLevel


class Monster(BaseModel, table=True):
    """Monster shared model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    dangerous_lvl: DangerLevel = Field(index=True)
    hp: int
    ac: int
    speed: int
    # Iteration 2: expose optional fields for API acceptance/return (DB columns already exist)
    type: Optional[str] = Field(default=None, index=True)
    size: Optional[str] = Field(default=None, index=True)
    alignment: Optional[str] = Field(default=None)
    hit_dice: Optional[str] = Field(default=None)
    speeds: Optional[Dict[str, int]] = Field(default=None, sa_type=JSONB)
    cr: Optional[float] = Field(default=None, index=True)
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
    traits: Optional[List[Dict[str, str]]] = Field(default=None, sa_type=JSONB)
    actions: Optional[List[Dict[str, str]]] = Field(default=None, sa_type=JSONB)
    reactions: Optional[List[Dict[str, str]]] = Field(default=None, sa_type=JSONB)
    legendary_actions: Optional[List[Dict[str, str]]] = Field(default=None, sa_type=JSONB)
    spellcasting: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSONB)
    tags: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()))


