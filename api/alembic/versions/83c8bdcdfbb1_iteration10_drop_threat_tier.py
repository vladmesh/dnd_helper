"""iteration10_drop_threat_tier

Revision ID: 83c8bdcdfbb1
Revises: 324555b64bbe
Create Date: 2025-09-01 19:49:11.809117

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401
import sqlmodel # noqa: F401


# revision identifiers, used by Alembic.
revision = '83c8bdcdfbb1'
down_revision = '324555b64bbe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop column threat_tier if exists
    with op.batch_alter_table('monster') as batch_op:
        batch_op.drop_column('threat_tier')


def downgrade() -> None:
    # Recreate column threat_tier as SmallInteger nullable with index
    with op.batch_alter_table('monster') as batch_op:
        batch_op.add_column(sa.Column('threat_tier', sa.SmallInteger(), nullable=True))
    op.create_index(op.f('ix_monster_threat_tier'), 'monster', ['threat_tier'], unique=False)


