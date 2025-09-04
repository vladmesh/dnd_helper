from typing import Any, Dict, List, Optional
from pydantic import field_validator

from sqlalchemy import Enum, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field

from .base import BaseModel
from .enums import CasterClass, SpellSchool


class Spell(BaseModel, table=True):
    """Spell shared model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    # Deprecated: single caster_class removed in favor of multi-class `classes`
    # caster_class: CasterClass = Field(index=True)
    school: SpellSchool = Field(sa_type=Text(), index=True)

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
        sa_type=ARRAY(Text()),
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
    slug: Optional[str] = Field(default=None, index=True)



    # Validators to coerce DB strings into Python Enums before serialization
    @field_validator("school", mode="before")
    @classmethod
    def _coerce_school_enum(cls, value: Any) -> Any:
        if value is None or isinstance(value, SpellSchool):
            return value
        try:
            return SpellSchool(value)
        except Exception as exc:  # keep strictness: invalid values should fail
            raise ValueError(f"Invalid SpellSchool: {value}") from exc

    @field_validator("classes", mode="before")
    @classmethod
    def _coerce_classes_enum_list(cls, value: Any) -> Any:
        if value is None:
            return value
        # Accept a single item (str/enum) and convert to list
        if not isinstance(value, list):
            value = [value]
        result: List[CasterClass] = []
        for item in value:
            if isinstance(item, CasterClass):
                result.append(item)
            else:
                try:
                    result.append(CasterClass(item))
                except Exception as exc:
                    raise ValueError(f"Invalid CasterClass: {item}") from exc
        return result

