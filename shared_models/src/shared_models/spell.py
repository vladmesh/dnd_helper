from typing import Optional

from sqlmodel import Field

from .base import BaseModel
from .enums import CasterClass, SpellSchool


class Spell(BaseModel, table=True):
    """Spell shared model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    description: str
    caster_class: CasterClass = Field(index=True)
    distance: int
    school: SpellSchool = Field(index=True)


