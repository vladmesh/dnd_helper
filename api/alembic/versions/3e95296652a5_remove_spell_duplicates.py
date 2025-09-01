"""remove_spell_duplicates

Revision ID: 3e95296652a5
Revises: 9d5790da60ad
Create Date: 2025-08-31 23:00:36.874969

"""
import sqlalchemy as sa  # noqa: F401
import sqlmodel  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = '3e95296652a5'
down_revision = '9d5790da60ad'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill classes from caster_class where missing, then drop duplicates
    # Ensure index on caster_class is dropped before column removal (if exists)
    try:
        op.drop_index(op.f('ix_spell_caster_class'), table_name='spell')
    except Exception:
        # Index may already be absent
        pass

    # Backfill: add caster_class into classes array if not present
    op.execute(
        """
        UPDATE spell
        SET classes = CASE
            WHEN caster_class IS NULL THEN classes
            WHEN classes IS NULL THEN ARRAY[caster_class]
            WHEN NOT (classes @> ARRAY[caster_class]) THEN array_append(classes, caster_class)
            ELSE classes
        END
        """
    )

    # Drop columns
    with op.batch_alter_table('spell') as batch_op:
        # Remove single-class column in favor of classes[]
        batch_op.drop_column('caster_class')
        # Remove deprecated boolean in favor of is_concentration
        try:
            batch_op.drop_column('concentration')
        except Exception:
            # Column may already be removed in some environments
            pass


def downgrade() -> None:
    # Recreate columns (without data restore beyond defaults)
    with op.batch_alter_table('spell') as batch_op:
        batch_op.add_column(sa.Column('caster_class', sa.Enum('WIZARD', 'SORCERER', 'CLERIC', 'DRUID', 'PALADIN', 'RANGER', 'BARD', 'WARLOCK', name='casterclass'), nullable=True))
        batch_op.add_column(sa.Column('concentration', sa.Boolean(), nullable=True))
    try:
        op.create_index(op.f('ix_spell_caster_class'), 'spell', ['caster_class'], unique=False)
    except Exception:
        pass


