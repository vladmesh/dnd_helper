"""rename monster.abilities to ability_scores; add Skill enum validators

Revision ID: 18658707bc59
Revises: 1f5c0f946a86
Create Date: 2025-09-12 19:09:22.398364

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401
import sqlmodel # noqa: F401


# revision identifiers, used by Alembic.
revision = '18658707bc59'
down_revision = '1f5c0f946a86'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename column abilities -> ability_scores on monster table
    with op.batch_alter_table('monster') as batch_op:
        batch_op.alter_column('abilities', new_column_name='ability_scores')


def downgrade() -> None:
    with op.batch_alter_table('monster') as batch_op:
        batch_op.alter_column('ability_scores', new_column_name='abilities')


