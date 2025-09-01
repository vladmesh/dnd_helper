"""iteration6_backfill_slug_and_casting_time

Revision ID: 3f599b20c4df
Revises: 51e1a43dd399
Create Date: 2025-08-31 21:48:41.583878

"""
import sqlalchemy as sa  # noqa: F401
import sqlmodel  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = '3f599b20c4df'
down_revision = '51e1a43dd399'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill slug for monsters from name when missing
    op.execute(
        """
        UPDATE monster
        SET slug = trim(both '-' from regexp_replace(lower(name), '[^a-z0-9]+', '-', 'g'))
        WHERE slug IS NULL AND name IS NOT NULL
        """
    )

    # Backfill slug for spells from name when missing
    op.execute(
        """
        UPDATE spell
        SET slug = trim(both '-' from regexp_replace(lower(name), '[^a-z0-9]+', '-', 'g'))
        WHERE slug IS NULL AND name IS NOT NULL
        """
    )

    # Normalize casting_time for spells to a finite set
    op.execute(
        """
        UPDATE spell
        SET casting_time = CASE
            WHEN casting_time IS NULL THEN NULL
            WHEN lower(casting_time) LIKE '%bonus action%' THEN 'bonus_action'
            WHEN lower(casting_time) LIKE '%reaction%' THEN 'reaction'
            WHEN lower(casting_time) = 'action' OR lower(casting_time) LIKE '%1 action%' THEN 'action'
            WHEN lower(casting_time) LIKE '10m%' OR lower(casting_time) LIKE '%10 min%' OR lower(casting_time) LIKE '%10 minute%' THEN '10m'
            WHEN lower(casting_time) LIKE '1m%' OR lower(casting_time) LIKE '%1 min%' OR lower(casting_time) LIKE '%1 minute%' THEN '1m'
            WHEN lower(casting_time) LIKE '8h%' OR lower(casting_time) LIKE '%8 hour%' THEN '8h'
            WHEN lower(casting_time) LIKE '1h%' OR lower(casting_time) LIKE '%1 hour%' THEN '1h'
            ELSE lower(casting_time)
        END
        WHERE casting_time IS NOT NULL
        """
    )


def downgrade() -> None:
    # Data-only normalization; no automatic downgrade.
    return


