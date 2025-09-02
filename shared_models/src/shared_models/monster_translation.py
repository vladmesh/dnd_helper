from typing import Optional

from sqlalchemy import UniqueConstraint, String
from sqlalchemy.dialects.postgresql import TEXT
from sqlmodel import Field

from .base import BaseModel
from .enums import Language


class MonsterTranslation(BaseModel, table=True):
    """Localized content for Monster."""

    __tablename__ = "monster_translations"
    __table_args__ = (
        UniqueConstraint("monster_id", "lang", name="uq_monster_translation_lang"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    monster_id: int = Field(foreign_key="monster.id", index=True)
    lang: Language = Field(sa_type=String(), index=True)

    name: str = Field(index=True)
    description: str = Field(sa_type=TEXT)

    # Optional relationship backref, defined here to avoid import cycles
    # The Monster model may define `translations` Relationship as well
    # monster: "Monster" = Relationship(back_populates="translations")
