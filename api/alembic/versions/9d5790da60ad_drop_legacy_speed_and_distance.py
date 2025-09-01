"""drop_legacy_speed_and_distance

Revision ID: 9d5790da60ad
Revises: be86dea0ce86
Create Date: 2025-08-31 22:11:54.684957

"""
import sqlalchemy as sa  # noqa: F401
import sqlmodel  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = '9d5790da60ad'
down_revision = 'be86dea0ce86'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop legacy columns
    with op.batch_alter_table('monster') as batch_op:
        # Remove scalar legacy speed and JSONB speeds source
        batch_op.drop_column('speed')
        batch_op.drop_column('speeds')

    with op.batch_alter_table('spell') as batch_op:
        batch_op.drop_column('distance')


def downgrade() -> None:
    # Recreate columns with generic types; data cannot be restored
    with op.batch_alter_table('monster') as batch_op:
        batch_op.add_column(sa.Column('speed', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('speeds', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    with op.batch_alter_table('spell') as batch_op:
        batch_op.add_column(sa.Column('distance', sa.Integer(), nullable=True))


