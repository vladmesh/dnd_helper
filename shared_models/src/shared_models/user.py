from typing import Optional

from sqlalchemy import BigInteger, String
from sqlmodel import Field

from .base import BaseModel
from .enums import Language


class User(BaseModel, table=True):
    """Basic Telegram user representation shared across services."""

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(index=True, sa_type=BigInteger())
    name: str
    is_admin: bool = Field(default=False)
    lang: Language = Field(sa_type=String(), default=Language.RU)


