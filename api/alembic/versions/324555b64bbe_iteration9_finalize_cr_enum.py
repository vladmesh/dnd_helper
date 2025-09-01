"""iteration9_finalize_cr_enum

Revision ID: 324555b64bbe
Revises: 5d7dbf11d3b3
Create Date: 2025-09-01 19:43:27.035704

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401
import sqlmodel # noqa: F401
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '324555b64bbe'
down_revision = '5d7dbf11d3b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create temp text column for CR strings
    op.add_column('monster', sa.Column('cr_new', sa.String(), nullable=True))
    conn = op.get_bind()

    # Prefer existing cr_enum if present
    conn.execute(sa.text("UPDATE monster SET cr_new = cr_enum::text WHERE cr_enum IS NOT NULL"))

    # Backfill from numeric cr where cr_enum is NULL
    # Fractions
    conn.execute(sa.text("UPDATE monster SET cr_new = '1/8' WHERE cr_enum IS NULL AND cr = 0.125"))
    conn.execute(sa.text("UPDATE monster SET cr_new = '1/4' WHERE cr_enum IS NULL AND cr = 0.25"))
    conn.execute(sa.text("UPDATE monster SET cr_new = '1/2' WHERE cr_enum IS NULL AND cr = 0.5"))
    # Integers 1..30
    for i in range(1, 31):
        conn.execute(
            sa.text("UPDATE monster SET cr_new = :val WHERE cr_enum IS NULL AND cr = :num"),
            {"val": str(i), "num": float(i)},
        )

    # Drop old cr, rename cr_new -> cr
    op.drop_column('monster', 'cr')
    op.alter_column('monster', 'cr_new', new_column_name='cr', existing_type=sa.String(), existing_nullable=True)

    # Drop legacy columns
    op.drop_column('monster', 'dangerous_lvl')
    op.drop_column('monster', 'cr_enum')


def downgrade() -> None:
    # Recreate legacy columns
    op.add_column('monster', sa.Column('cr_enum', postgresql.ENUM('CR_1_8', 'CR_1_4', 'CR_1_2', 'CR_1', 'CR_2', 'CR_3', 'CR_4', 'CR_5', 'CR_6', 'CR_7', 'CR_8', 'CR_9', 'CR_10', 'CR_11', 'CR_12', 'CR_13', 'CR_14', 'CR_15', 'CR_16', 'CR_17', 'CR_18', 'CR_19', 'CR_20', 'CR_21', 'CR_22', 'CR_23', 'CR_24', 'CR_25', 'CR_26', 'CR_27', 'CR_28', 'CR_29', 'CR_30', name='challengerating'), autoincrement=False, nullable=True))
    op.add_column('monster', sa.Column('dangerous_lvl', postgresql.ENUM('TRIVIAL', 'LOW', 'MODERATE', 'HIGH', 'DEADLY', name='dangerlevel'), autoincrement=False, nullable=True))

    # Create temp numeric column to restore numeric cr
    op.add_column('monster', sa.Column('cr_num', sa.DOUBLE_PRECISION(precision=53), nullable=True))
    conn = op.get_bind()
    # Fractions
    conn.execute(sa.text("UPDATE monster SET cr_num = 0.125 WHERE cr = '1/8'"))
    conn.execute(sa.text("UPDATE monster SET cr_num = 0.25 WHERE cr = '1/4'"))
    conn.execute(sa.text("UPDATE monster SET cr_num = 0.5 WHERE cr = '1/2'"))
    # Integers 1..30
    for i in range(1, 31):
        conn.execute(sa.text("UPDATE monster SET cr_num = :num WHERE cr = :val"), {"val": str(i), "num": float(i)})

    # Swap columns back
    op.drop_column('monster', 'cr')
    op.alter_column('monster', 'cr_num', new_column_name='cr', existing_type=sa.DOUBLE_PRECISION(precision=53), existing_nullable=True)


