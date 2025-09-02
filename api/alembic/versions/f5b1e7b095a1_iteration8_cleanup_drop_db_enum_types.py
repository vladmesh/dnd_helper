"""iteration8_cleanup_drop_db_enum_types

Revision ID: f5b1e7b095a1
Revises: 160c6fd4ba34
Create Date: 2025-09-02 21:38:37.445110

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401
import sqlmodel # noqa: F401
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f5b1e7b095a1'
down_revision = '160c6fd4ba34'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop leftover DB enum types if they exist and are unused
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'language') THEN
                DROP TYPE language;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'casterclass') THEN
                DROP TYPE casterclass;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'spellschool') THEN
                DROP TYPE spellschool;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'dangerlevel') THEN
                DROP TYPE dangerlevel;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'challengerating') THEN
                DROP TYPE challengerating;
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    # No-op: enum types are optional cleanup artifacts
    pass


