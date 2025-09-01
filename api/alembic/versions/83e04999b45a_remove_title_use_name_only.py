"""remove_title_use_name_only

Revision ID: 83e04999b45a
Revises: 5e102bd3b27d
Create Date: 2025-08-29 23:42:11.146362

"""
import sqlalchemy as sa  # noqa: F401
import sqlmodel  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = '83e04999b45a'
down_revision = '5e102bd3b27d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill name from title where name is NULL
    op.execute("UPDATE monster SET name = COALESCE(name, title)")
    op.execute("UPDATE spell SET name = COALESCE(name, title)")

    # Drop title columns
    with op.batch_alter_table('monster') as batch_op:
        # Ensure name is not null going forward
        batch_op.alter_column('name', existing_type=sa.String(), nullable=False)
        # Drop title if exists
        try:
            batch_op.drop_column('title')
        except Exception:
            pass

    with op.batch_alter_table('spell') as batch_op:
        batch_op.alter_column('name', existing_type=sa.String(), nullable=False)
        try:
            batch_op.drop_column('title')
        except Exception:
            pass


def downgrade() -> None:
    # Re-create title as nullable and copy from name
    with op.batch_alter_table('monster') as batch_op:
        batch_op.add_column(sa.Column('title', sa.String(), nullable=True))
    op.execute("UPDATE monster SET title = name WHERE title IS NULL")

    with op.batch_alter_table('spell') as batch_op:
        batch_op.add_column(sa.Column('title', sa.String(), nullable=True))
    op.execute("UPDATE spell SET title = name WHERE title IS NULL")

    # Optionally relax NOT NULL on name (keep strictness)


