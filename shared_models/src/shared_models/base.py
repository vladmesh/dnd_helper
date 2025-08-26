from datetime import datetime

from sqlalchemy import DateTime, func
from sqlmodel import Field, SQLModel


class BaseModel(SQLModel, table=False):
    """Abstract base for ORM models with audit timestamps."""

    # Use per-model columns via sa_type + sa_column_kwargs to avoid reusing
    # the same SQLAlchemy Column instance across multiple tables.
    created_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now(), "nullable": True},
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(),
            "nullable": True,
        },
    )


