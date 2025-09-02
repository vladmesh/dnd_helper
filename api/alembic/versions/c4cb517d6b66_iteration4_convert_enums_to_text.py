"""iteration4_convert_enums_to_text

Revision ID: c4cb517d6b66
Revises: 7148f7999c97
Create Date: 2025-09-01 21:33:12.702576

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401
import sqlmodel # noqa: F401


# revision identifiers, used by Alembic.
revision = 'c4cb517d6b66'
down_revision = '7148f7999c97'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert translation language columns from DB ENUM to TEXT (if needed)
    op.execute("ALTER TABLE monster_translations ALTER COLUMN lang TYPE VARCHAR(2) USING lang::text")
    op.execute("ALTER TABLE spell_translations ALTER COLUMN lang TYPE VARCHAR(2) USING lang::text")
    # Ensure enum_translations.lang is TEXT as well (no-op if already text with CHECK)
    op.execute("ALTER TABLE enum_translations ALTER COLUMN lang TYPE VARCHAR(2) USING lang::text")

    # Convert spell.school from ENUM to TEXT
    op.execute("ALTER TABLE spell ALTER COLUMN school TYPE TEXT USING school::text")

    # Convert spell.classes from casterclass[] to text[] via temp column
    op.execute("ALTER TABLE spell ADD COLUMN classes_txt text[]")
    op.execute(
        """
        UPDATE spell
        SET classes_txt = CASE
            WHEN classes IS NULL THEN NULL
            ELSE ARRAY(SELECT unnest(classes)::text)
        END
        """
    )
    op.execute("ALTER TABLE spell DROP COLUMN classes")
    op.execute("ALTER TABLE spell RENAME COLUMN classes_txt TO classes")

    # Drop obsolete enum types if they exist and are unused
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'language') THEN
                DROP TYPE language;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'casterclass') THEN
                DROP TYPE casterclass;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'spellschool') THEN
                DROP TYPE spellschool;
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    # Best-effort downgrade: recreate enum types and convert back
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'language') THEN
                CREATE TYPE language AS ENUM ('RU', 'EN');
            END IF;
        END$$;
        """
    )
    op.execute("ALTER TABLE monster_translations ALTER COLUMN lang TYPE language USING lang::language")
    op.execute("ALTER TABLE spell_translations ALTER COLUMN lang TYPE language USING lang::language")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'spellschool') THEN
                CREATE TYPE spellschool AS ENUM (
                    'abjuration','conjuration','divination','enchantment','evocation','illusion','necromancy','transmutation'
                );
            END IF;
        END$$;
        """
    )
    op.execute("ALTER TABLE spell ALTER COLUMN school TYPE spellschool USING school::spellschool")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'casterclass') THEN
                CREATE TYPE casterclass AS ENUM ('wizard','sorcerer','cleric','druid','paladin','ranger','bard','warlock');
            END IF;
        END$$;
        """
    )
    op.execute("ALTER TABLE spell ADD COLUMN classes_tmp casterclass[]")
    op.execute(
        """
        UPDATE spell
        SET classes_tmp = CASE
            WHEN classes IS NULL THEN NULL
            ELSE ARRAY(SELECT unnest(classes)::casterclass)
        END
        """
    )
    op.execute("ALTER TABLE spell DROP COLUMN classes")
    op.execute("ALTER TABLE spell RENAME COLUMN classes_tmp TO classes")


