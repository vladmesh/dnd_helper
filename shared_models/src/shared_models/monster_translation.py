from typing import Any, Dict, List, Optional

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TEXT
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

    # Localized text blocks
    traits: Optional[List[Dict[str, str]]] = Field(default=None, sa_type=JSONB)
    actions: Optional[List[Dict[str, str]]] = Field(default=None, sa_type=JSONB)
    reactions: Optional[List[Dict[str, str]]] = Field(default=None, sa_type=JSONB)
    legendary_actions: Optional[List[Dict[str, str]]] = Field(default=None, sa_type=JSONB)
    spellcasting: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSONB)

    # Languages as human-readable text (moved from Monster.languages)
    languages_text: Optional[str] = Field(default=None, sa_type=TEXT)

    # Optional relationship backref, defined here to avoid import cycles
    # The Monster model may define `translations` Relationship as well
    # monster: "Monster" = Relationship(back_populates="translations")
