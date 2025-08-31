"""iteration5_add_gin_indexes

Revision ID: 51e1a43dd399
Revises: 2fc716665de3
Create Date: 2025-08-31 21:43:30.172702

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401
import sqlmodel # noqa: F401


# revision identifiers, used by Alembic.
revision = '51e1a43dd399'
down_revision = '2fc716665de3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # GIN indexes on ARRAY columns to speed up contains/overlap queries
    op.create_index('ix_monster_languages_gin', 'monster', ['languages'], unique=False, postgresql_using='gin')
    op.create_index('ix_monster_damage_immunities_gin', 'monster', ['damage_immunities'], unique=False, postgresql_using='gin')
    op.create_index('ix_monster_damage_resistances_gin', 'monster', ['damage_resistances'], unique=False, postgresql_using='gin')
    op.create_index('ix_monster_damage_vulnerabilities_gin', 'monster', ['damage_vulnerabilities'], unique=False, postgresql_using='gin')
    op.create_index('ix_monster_condition_immunities_gin', 'monster', ['condition_immunities'], unique=False, postgresql_using='gin')
    op.create_index('ix_monster_environments_gin', 'monster', ['environments'], unique=False, postgresql_using='gin')
    op.create_index('ix_monster_roles_gin', 'monster', ['roles'], unique=False, postgresql_using='gin')
    op.create_index('ix_monster_tags_gin', 'monster', ['tags'], unique=False, postgresql_using='gin')

    op.create_index('ix_spell_classes_gin', 'spell', ['classes'], unique=False, postgresql_using='gin')
    op.create_index('ix_spell_tags_gin', 'spell', ['tags'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('ix_spell_tags_gin', table_name='spell')
    op.drop_index('ix_spell_classes_gin', table_name='spell')

    op.drop_index('ix_monster_tags_gin', table_name='monster')
    op.drop_index('ix_monster_roles_gin', table_name='monster')
    op.drop_index('ix_monster_environments_gin', table_name='monster')
    op.drop_index('ix_monster_condition_immunities_gin', table_name='monster')
    op.drop_index('ix_monster_damage_vulnerabilities_gin', table_name='monster')
    op.drop_index('ix_monster_damage_resistances_gin', table_name='monster')
    op.drop_index('ix_monster_damage_immunities_gin', table_name='monster')
    op.drop_index('ix_monster_languages_gin', table_name='monster')


