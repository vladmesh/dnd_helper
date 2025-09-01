from typing import Optional

from sqlalchemy import Enum as SAEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import TEXT
from sqlmodel import Field

from .base import BaseModel
from .enums import Language


class SpellTranslation(BaseModel, table=True):
    """Localized content for Spell."""

    __tablename__ = "spell_translations"
    __table_args__ = (
        UniqueConstraint("spell_id", "lang", name="uq_spell_translation_lang"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    spell_id: int = Field(foreign_key="spell.id", index=True)
    lang: Language = Field(sa_type=SAEnum(Language, name="language"), index=True)

    name: str = Field(index=True)
    description: str = Field(sa_type=TEXT)

    # Optional relationship backref
    # spell: "Spell" = Relationship(back_populates="translations")
