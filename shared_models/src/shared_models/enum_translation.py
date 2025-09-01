from typing import Optional

from sqlalchemy import Enum as SAEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TEXT
from sqlmodel import Field

from .base import BaseModel
from .enums import Language


class EnumTranslation(BaseModel, table=True):
    """Localized labels and metadata for enum codes.

    Uniqueness is enforced per (enum_type, enum_value, lang).
    """

    __tablename__ = "enum_translations"
    __table_args__ = (
        UniqueConstraint(
            "enum_type", "enum_value", "lang", name="uq_enum_translation_lang"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    # Enum identification
    enum_type: str = Field(index=True)
    enum_value: str = Field(index=True)

    # Target language
    lang: Language = Field(sa_type=SAEnum(Language, name="language"), index=True)

    # Localized content
    label: str = Field(index=True)
    description: Optional[str] = Field(default=None, sa_type=TEXT)
    synonyms: Optional[dict] = Field(default=None, sa_type=JSONB)


