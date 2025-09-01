"""backfill_derived_fields_iter4

Revision ID: 2fc716665de3
Revises: 8263fcad25be
Create Date: 2025-08-31 21:37:52.435988

"""
import sqlalchemy as sa  # noqa: F401
import sqlmodel  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = '2fc716665de3'
down_revision = '8263fcad25be'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Monsters: backfill derived fields from JSONB sources
    op.execute(
        """
        UPDATE monster
        SET
          speed_walk = CASE WHEN speeds ? 'walk' THEN (speeds->>'walk')::int ELSE NULL END,
          speed_fly = CASE WHEN speeds ? 'fly' THEN (speeds->>'fly')::int ELSE NULL END,
          speed_swim = CASE WHEN speeds ? 'swim' THEN (speeds->>'swim')::int ELSE NULL END,
          speed_climb = CASE WHEN speeds ? 'climb' THEN (speeds->>'climb')::int ELSE NULL END,
          speed_burrow = CASE WHEN speeds ? 'burrow' THEN (speeds->>'burrow')::int ELSE NULL END,
          is_flying = CASE WHEN speeds ? 'fly' THEN ((speeds->>'fly')::int > 0) ELSE NULL END,
          has_darkvision = CASE WHEN senses ? 'darkvision' THEN ((senses->>'darkvision')::int > 0) ELSE NULL END,
          darkvision_range = CASE WHEN senses ? 'darkvision' THEN (senses->>'darkvision')::int ELSE NULL END,
          has_blindsight = CASE WHEN senses ? 'blindsight' THEN ((senses->>'blindsight')::int > 0) ELSE NULL END,
          blindsight_range = CASE WHEN senses ? 'blindsight' THEN (senses->>'blindsight')::int ELSE NULL END,
          has_truesight = CASE WHEN senses ? 'truesight' THEN ((senses->>'truesight')::int > 0) ELSE NULL END,
          truesight_range = CASE WHEN senses ? 'truesight' THEN (senses->>'truesight')::int ELSE NULL END,
          tremorsense_range = CASE WHEN senses ? 'tremorsense' THEN (senses->>'tremorsense')::int ELSE NULL END
        WHERE speeds IS NOT NULL OR senses IS NOT NULL
        """
    )

    # Spells: backfill derived fast-filter fields
    # is_concentration from duration string presence
    op.execute(
        """
        UPDATE spell
        SET is_concentration = CASE
            WHEN duration IS NULL THEN NULL
            WHEN lower(duration) LIKE '%concentration%' THEN TRUE
            ELSE FALSE
        END
        WHERE duration IS NOT NULL OR is_concentration IS NULL
        """
    )

    # damage_type from damage JSON
    op.execute(
        """
        UPDATE spell
        SET damage_type = CASE WHEN damage ? 'type' THEN damage->>'type' ELSE damage_type END
        WHERE damage IS NOT NULL
        """
    )

    # save_ability from saving_throw JSON
    op.execute(
        """
        UPDATE spell
        SET save_ability = CASE WHEN saving_throw ? 'ability' THEN saving_throw->>'ability' ELSE save_ability END
        WHERE saving_throw IS NOT NULL
        """
    )

    # attack_roll heuristic: set true when damage present and no save ability
    op.execute(
        """
        UPDATE spell
        SET attack_roll = TRUE
        WHERE attack_roll IS NULL AND damage IS NOT NULL AND NOT (saving_throw ? 'ability')
        """
    )

    # targeting heuristic: if area present, infer POINT
    op.execute(
        """
        UPDATE spell
        SET targeting = 'POINT'
        WHERE targeting IS NULL AND area IS NOT NULL
        """
    )


def downgrade() -> None:
    # Backfill is data-only and idempotent; no automatic downgrade.
    # Intentionally left as a no-op.
    return


