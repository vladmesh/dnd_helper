"""iteration6_monster_translations_text_blocks

Revision ID: 160c6fd4ba34
Revises: c4cb517d6b66
Create Date: 2025-09-02 21:19:16.877366

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401
import sqlmodel # noqa: F401
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '160c6fd4ba34'
down_revision = 'c4cb517d6b66'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add localized text blocks to monster_translations
    op.add_column('monster_translations', sa.Column('traits', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('monster_translations', sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('monster_translations', sa.Column('reactions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('monster_translations', sa.Column('legendary_actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('monster_translations', sa.Column('spellcasting', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Drop localized text blocks
    op.drop_column('monster_translations', 'spellcasting')
    op.drop_column('monster_translations', 'legendary_actions')
    op.drop_column('monster_translations', 'reactions')
    op.drop_column('monster_translations', 'actions')
    op.drop_column('monster_translations', 'traits')


