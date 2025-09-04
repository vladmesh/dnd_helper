"""i18n: finalize constraints (names/descriptions not null)

Revision ID: 9b215e45f2ef
Revises: 7b3bf0ff5679
Create Date: 2025-09-04 22:06:36.097755

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401
import sqlmodel # noqa: F401


# revision identifiers, used by Alembic.
revision = '9b215e45f2ef'
down_revision = '7b3bf0ff5679'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure no NULLs remain before setting NOT NULL
    op.execute("UPDATE monster_translations SET name = '' WHERE name IS NULL;")
    op.execute("UPDATE monster_translations SET description = '' WHERE description IS NULL;")
    op.execute("UPDATE spell_translations SET name = '' WHERE name IS NULL;")
    op.execute("UPDATE spell_translations SET description = '' WHERE description IS NULL;")

    # Set NOT NULL constraints
    op.alter_column("monster_translations", "name", existing_type=sa.TEXT(), nullable=False)
    op.alter_column("monster_translations", "description", existing_type=sa.TEXT(), nullable=False)
    op.alter_column("spell_translations", "name", existing_type=sa.TEXT(), nullable=False)
    op.alter_column("spell_translations", "description", existing_type=sa.TEXT(), nullable=False)


def downgrade() -> None:
    # Revert NOT NULL constraints
    op.alter_column("spell_translations", "description", existing_type=sa.TEXT(), nullable=True)
    op.alter_column("spell_translations", "name", existing_type=sa.TEXT(), nullable=True)
    op.alter_column("monster_translations", "description", existing_type=sa.TEXT(), nullable=True)
    op.alter_column("monster_translations", "name", existing_type=sa.TEXT(), nullable=True)


