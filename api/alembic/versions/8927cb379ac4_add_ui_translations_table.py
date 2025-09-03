"""sync FKs for translations tables (no-op for ui_translations)

Revision ID: 8927cb379ac4
Revises: 817bc5a29a97
Create Date: 2025-09-03 00:04:12.923641

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401
import sqlmodel # noqa: F401


# revision identifiers, used by Alembic.
revision = '8927cb379ac4'
down_revision = '817bc5a29a97'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FK sync only
    op.drop_constraint(op.f('monster_translations_monster_id_fkey'), 'monster_translations', type_='foreignkey')
    op.create_foreign_key(None, 'monster_translations', 'monster', ['monster_id'], ['id'])
    op.drop_constraint(op.f('spell_translations_spell_id_fkey'), 'spell_translations', type_='foreignkey')
    op.create_foreign_key(None, 'spell_translations', 'spell', ['spell_id'], ['id'])


def downgrade() -> None:
    # Recreate original FKs with ON DELETE CASCADE
    op.drop_constraint(None, 'spell_translations', type_='foreignkey')
    op.create_foreign_key(op.f('spell_translations_spell_id_fkey'), 'spell_translations', 'spell', ['spell_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'monster_translations', type_='foreignkey')
    op.create_foreign_key(op.f('monster_translations_monster_id_fkey'), 'monster_translations', 'monster', ['monster_id'], ['id'], ondelete='CASCADE')


