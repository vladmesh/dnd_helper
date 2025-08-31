from typing import Any, Dict, List, Optional

from sqlmodel import Field
from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from .base import BaseModel
from .enums import CasterClass, SpellSchool


class Spell(BaseModel, table=True):
    """Spell shared model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    # Deprecated: single caster_class removed in favor of multi-class `classes`
    # caster_class: CasterClass = Field(index=True)
    school: SpellSchool = Field(index=True)

    # Iteration 1: additive fields to align with docs/fields.md (all optional)
    level: Optional[int] = Field(default=None, index=True)
    ritual: Optional[bool] = Field(default=None)
    casting_time: Optional[str] = Field(default=None)
    range: Optional[str] = Field(default=None)
    duration: Optional[str] = Field(default=None)
    # Deprecated: use `is_concentration` derived from `duration`
    # concentration: Optional[bool] = Field(default=None)
    components: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSONB)
    classes: Optional[List[CasterClass]] = Field(
        default=None,
        sa_type=ARRAY(Enum(CasterClass, name="casterclass")),
    )
    damage: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSONB)
    saving_throw: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSONB)
    area: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSONB)
    conditions: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()))
    tags: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()))

    # Iteration 2 — fast-filter duplicates and metadata (nullable; indexed where useful)
    is_concentration: Optional[bool] = Field(default=None, index=True)
    attack_roll: Optional[bool] = Field(default=None, index=True)
    damage_type: Optional[str] = Field(default=None, index=True)
    save_ability: Optional[str] = Field(default=None, index=True)
    targeting: Optional[str] = Field(default=None, index=True)
    # ritual (single definition with index)
    ritual: Optional[bool] = Field(default=None, index=True)

    # Metadata and localization
    source: Optional[str] = Field(default=None, index=True)
    page: Optional[int] = Field(default=None)
    name_ru: Optional[str] = Field(default=None, index=True)
    name_en: Optional[str] = Field(default=None, index=True)
    slug: Optional[str] = Field(default=None, index=True)


