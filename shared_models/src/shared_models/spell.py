from typing import Any, Dict, List, Optional

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, field_validator
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field

from .base import BaseModel
from .enums import Ability, CasterClass, DamageType, SpellSchool, Targeting


class SpellCreate(PydanticBaseModel):
    """Pydantic model for spell creation with validation."""
    school: str  # Will be validated against SpellSchool enum
    level: Optional[int] = None
    ritual: Optional[bool] = None
    casting_time: Optional[str] = None
    range: Optional[str] = None
    duration: Optional[str] = None
    components: Optional[Dict[str, Any]] = None
    classes: Optional[List[str]] = None  # Will be validated against CasterClass enum
    higher_level: Optional[str] = None
    material: Optional[str] = None
    tags: Optional[List[str]] = None
    slug: Optional[str] = None
    translations: Optional[Dict[str, Dict[str, Any]]] = None

    @field_validator('school')
    @classmethod
    def validate_school(cls, v):
        """Validate that school is a valid SpellSchool enum value."""
        try:
            SpellSchool(v)
            return v
        except ValueError:
            raise ValueError(f'Invalid school: {v}. Must be one of: {[e.value for e in SpellSchool]}')

    @field_validator('classes')
    @classmethod
    def validate_classes(cls, v):
        """Validate that all classes are valid CasterClass enum values."""
        if v is None:
            return v
        valid_classes = [e.value for e in CasterClass]
        for class_name in v:
            if class_name not in valid_classes:
                raise ValueError(f'Invalid class: {class_name}. Must be one of: {valid_classes}')
        return v


class Spell(BaseModel, table=True):
    """Spell shared model."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[int] = Field(default=None, primary_key=True)
    # Deprecated: single caster_class removed in favor of multi-class `classes`
    # caster_class: CasterClass = Field(index=True)
    school: SpellSchool = Field(sa_type=Text(), index=True)

    # Iteration 1: additive fields to align with docs/fields.md (all optional)
    level: Optional[int] = Field(default=None, index=True)
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

    # Validators for fast-filter enum-like fields stored as text codes
    @field_validator("damage_type", mode="before")
    @classmethod
    def _validate_damage_type(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, DamageType):
            return value.value
        if isinstance(value, str):
            v = value.strip().lower()
            if v not in {d.value for d in DamageType}:
                raise ValueError(f"Invalid damage_type: {value}")
            return v
        raise ValueError("damage_type must be a DamageType or string code")

    @field_validator("save_ability", mode="before")
    @classmethod
    def _validate_save_ability(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, Ability):
            return value.value
        if isinstance(value, str):
            v = value.strip().lower()
            if v not in {a.value for a in Ability}:
                raise ValueError(f"Invalid save_ability: {value}")
            return v
        raise ValueError("save_ability must be an Ability or string code")

    @field_validator("targeting", mode="before")
    @classmethod
    def _validate_targeting(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, Targeting):
            return value.value
        if isinstance(value, str):
            v = value.strip().lower()
            if v not in {t.value for t in Targeting}:
                raise ValueError(f"Invalid targeting: {value}")
            return v
        raise ValueError("targeting must be a Targeting or string code")

