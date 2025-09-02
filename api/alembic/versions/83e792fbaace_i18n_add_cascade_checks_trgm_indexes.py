"""i18n: add cascade, checks, trgm indexes

Revision ID: 83e792fbaace
Revises: 41cd6d4de9c8
Create Date: 2025-09-02 22:14:41.181587

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401
import sqlmodel # noqa: F401


# revision identifiers, used by Alembic.
revision = '83e792fbaace'
down_revision = '41cd6d4de9c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pg_trgm extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Recreate FKs with ON DELETE CASCADE for translation tables
    # monster_translations.monster_id -> monster(id)
    try:
        op.drop_constraint(
            "monster_translations_monster_id_fkey",
            "monster_translations",
            type_="foreignkey",
        )
    except Exception:
        # Constraint name may vary; ignore if not present
        pass
    op.create_foreign_key(
        "monster_translations_monster_id_fkey",
        "monster_translations",
        "monster",
        ["monster_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # spell_translations.spell_id -> spell(id)
    try:
        op.drop_constraint(
            "spell_translations_spell_id_fkey",
            "spell_translations",
            type_="foreignkey",
        )
    except Exception:
        pass
    op.create_foreign_key(
        "spell_translations_spell_id_fkey",
        "spell_translations",
        "spell",
        ["spell_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # CHECK constraints for lang columns (restrict to 'ru'/'en')
    op.create_check_constraint(
        "ck_monster_translations_lang",
        "monster_translations",
        "lang in ('ru','en')",
    )
    op.create_check_constraint(
        "ck_spell_translations_lang",
        "spell_translations",
        "lang in ('ru','en')",
    )
    op.create_check_constraint(
        "ck_enum_translations_lang",
        "enum_translations",
        "lang in ('ru','en')",
    )

    # GIN (trigram) indexes for fast LIKE/ILIKE on names and descriptions
    op.create_index(
        "ix_monster_translations_name_trgm",
        "monster_translations",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_spell_translations_name_trgm",
        "spell_translations",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    # Optional: description trigram indexes (can be large; keep for parity)
    op.create_index(
        "ix_monster_translations_description_trgm",
        "monster_translations",
        ["description"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"description": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_spell_translations_description_trgm",
        "spell_translations",
        ["description"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"description": "gin_trgm_ops"},
    )


def downgrade() -> None:
    # Drop trigram indexes
    for ix in (
        "ix_spell_translations_description_trgm",
        "ix_monster_translations_description_trgm",
        "ix_spell_translations_name_trgm",
        "ix_monster_translations_name_trgm",
    ):
        try:
            op.drop_index(ix)
        except Exception:
            pass

    # Drop CHECK constraints
    for (table, name) in (
        ("enum_translations", "ck_enum_translations_lang"),
        ("spell_translations", "ck_spell_translations_lang"),
        ("monster_translations", "ck_monster_translations_lang"),
    ):
        try:
            op.drop_constraint(name, table, type_="check")
        except Exception:
            pass

    # Recreate FKs without CASCADE (best-effort)
    try:
        op.drop_constraint(
            "spell_translations_spell_id_fkey",
            "spell_translations",
            type_="foreignkey",
        )
    except Exception:
        pass
    op.create_foreign_key(
        "spell_translations_spell_id_fkey",
        "spell_translations",
        "spell",
        ["spell_id"],
        ["id"],
    )

    try:
        op.drop_constraint(
            "monster_translations_monster_id_fkey",
            "monster_translations",
            type_="foreignkey",
        )
    except Exception:
        pass
    op.create_foreign_key(
        "monster_translations_monster_id_fkey",
        "monster_translations",
        "monster",
        ["monster_id"],
        ["id"],
    )


