"""iteration7_add_checks_monster_spell

Revision ID: be86dea0ce86
Revises: 3f599b20c4df
Create Date: 2025-08-31 21:56:26.944811

"""
import sqlalchemy as sa  # noqa: F401
import sqlmodel  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = 'be86dea0ce86'
down_revision = '3f599b20c4df'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add CHECK constraint for spell.level in range 0..9 (or NULL)
    op.create_check_constraint(
        constraint_name="ck_spell_level_range",
        table_name="spell",
        condition="(level IS NULL) OR (level BETWEEN 0 AND 9)",
    )

    # Add CHECK constraints for monster.size and monster.type as case-insensitive enums
    op.create_check_constraint(
        constraint_name="ck_monster_size_enum",
        table_name="monster",
        condition=(
            "(size IS NULL) OR (lower(size) IN ("
            "'tiny','small','medium','large','huge','gargantuan'" 
            "))"
        ),
    )

    op.create_check_constraint(
        constraint_name="ck_monster_type_enum",
        table_name="monster",
        condition=(
            "(type IS NULL) OR (lower(type) IN ("
            "'aberration','beast','celestial','construct','dragon','elemental',"
            "'fey','fiend','giant','humanoid','monstrosity','ooze','plant','undead'"
            "))"
        ),
    )


def downgrade() -> None:
    op.drop_constraint("ck_monster_type_enum", table_name="monster", type_="check")
    op.drop_constraint("ck_monster_size_enum", table_name="monster", type_="check")
    op.drop_constraint("ck_spell_level_range", table_name="spell", type_="check")


