from typing import Optional

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from .base import BaseModel


class AdminAudit(BaseModel, table=True):
    """Administrative audit log for changes made via admin UI.

    Keep minimal but useful fields; do not store secrets.
    """

    __tablename__ = "admin_audit"

    id: Optional[int] = Field(default=None, primary_key=True)

    table_name: str = Field(index=True)
    row_pk: str = Field(index=True)
    operation: str = Field(index=True)  # "create" | "update" | "delete"

    before_data: Optional[dict] = Field(default=None, sa_type=JSONB)
    after_data: Optional[dict] = Field(default=None, sa_type=JSONB)

    actor: Optional[str] = Field(default=None, index=True)
    path: Optional[str] = Field(default=None)
    client_ip: Optional[str] = Field(default=None, index=True)


