"""Shared SQLModel models package.

Place SQLModel ORM and validation models here to be reused across services.
"""

from .base import BaseModel
from .user import User

__all__ = [
    "BaseModel",
    "User",
]


