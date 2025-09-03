from typing import Optional

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TEXT
from sqlmodel import Field

from .base import BaseModel
from .enums import Language


class UiTranslation(BaseModel, table=True):
    """UI translation key-value storage scoped by namespace and language."""

    __tablename__ = "ui_translations"
    __table_args__ = (
        UniqueConstraint("namespace", "key", "lang", name="uq_ui_translation_lang"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    namespace: str = Field(index=True)
    key: str = Field(index=True)
    lang: Language = Field(sa_type=String(), index=True)
    text: str = Field(sa_type=TEXT)


