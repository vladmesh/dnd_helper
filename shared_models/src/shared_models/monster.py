from typing import Optional

from sqlmodel import Field

from .base import BaseModel
from .enums import DangerLevel


class Monster(BaseModel, table=True):
    """Monster shared model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str | None = Field(default=None, index=True)
    description: str
    dangerous_lvl: DangerLevel = Field(index=True)
    hp: int
    ac: int
    speed: int


