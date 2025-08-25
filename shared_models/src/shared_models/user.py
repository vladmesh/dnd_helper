from typing import Optional

from sqlmodel import Field

from .base import BaseModel


class User(BaseModel, table=True):
    """Basic Telegram user representation shared across services."""

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(index=True)
    name: str


