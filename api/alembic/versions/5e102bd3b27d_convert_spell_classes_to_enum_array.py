"""convert_spell_classes_to_enum_array

Revision ID: 5e102bd3b27d
Revises: 81bc403bc7e5
Create Date: 2025-08-29 23:12:39.221389

"""
import sqlalchemy as sa  # noqa: F401
import sqlmodel  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = '5e102bd3b27d'
down_revision = '81bc403bc7e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type matching shared_models.enums.CasterClass values
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'casterclass') THEN
                CREATE TYPE casterclass AS ENUM (
                    'wizard',
                    'sorcerer',
                    'cleric',
                    'druid',
                    'paladin',
                    'ranger',
                    'bard',
                    'warlock'
                );
            END IF;
        END$$;
        """
    )

    # Convert column using a temporary column (USING doesn't allow subquery in transform)
    op.execute("ALTER TABLE spell ADD COLUMN classes_tmp casterclass[]")
    op.execute(
        """
        UPDATE spell
        SET classes_tmp = CASE
            WHEN classes IS NULL THEN NULL
            ELSE ARRAY(SELECT unnest(classes)::casterclass)
        END
        """
    )
    op.execute("ALTER TABLE spell DROP COLUMN classes")
    op.execute("ALTER TABLE spell RENAME COLUMN classes_tmp TO classes")


def downgrade() -> None:
    # Revert using a temporary column, then drop enum type
    op.execute("ALTER TABLE spell ADD COLUMN classes_tmp text[]")
    op.execute(
        """
        UPDATE spell
        SET classes_tmp = CASE
            WHEN classes IS NULL THEN NULL
            ELSE ARRAY(SELECT unnest(classes)::text)
        END
        """
    )
    op.execute("ALTER TABLE spell DROP COLUMN classes")
    op.execute("ALTER TABLE spell RENAME COLUMN classes_tmp TO classes")

    # Drop enum type if exists (no longer referenced)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'casterclass') THEN
                DROP TYPE casterclass;
            END IF;
        END$$;
        """
    )


