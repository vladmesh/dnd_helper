from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from .base import BaseModel


class AdminJob(BaseModel, table=True):
    """Admin operations job descriptor stored in DB for async processing.

    Store minimal metadata for resumable, auditable imports.
    """

    __tablename__ = "admin_jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)

    job_type: str = Field(index=True)
    args: Optional[dict] = Field(default=None, sa_type=JSONB)
    file_path: Optional[str] = Field(default=None)

    status: str = Field(index=True)  # queued | running | succeeded | failed
    counters: Optional[dict] = Field(default=None, sa_type=JSONB)
    error: Optional[str] = Field(default=None)

    launched_by: Optional[str] = Field(default=None, index=True)

    started_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"nullable": True},
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"nullable": True},
    )

