from typing import Optional

from dnd_helper_api.db import get_session
from dnd_helper_api.routers.spells import logger, router
from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import delete
from sqlmodel import Session, select

from shared_models import Spell
from shared_models.enums import CasterClass, SpellSchool
from shared_models.spell_translation import SpellTranslation

from .derived import _compute_spell_derived_fields
from .translations import _select_language


@router.post("", response_model=Spell, status_code=status.HTTP_201_CREATED)
async def create_spell(
    spell: Spell,
    lang: Optional[str] = None,
    request: Request = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> Spell:
    # Strict extra-fields validation against Spell model + "translations"
    try:
        body = await request.json() if request is not None else {}
    except Exception:
        body = {}
    if isinstance(body, dict):
        allowed_keys = set(Spell.model_fields.keys()) | {"translations"}
        extra_keys = set(body.keys()) - allowed_keys
        if extra_keys:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unexpected fields: {sorted(extra_keys)}")
        # Validate enum-like fields strictly
        school_value = body.get("school")
        if school_value is not None:
            try:
                SpellSchool(str(school_value))
            except Exception:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid value for 'school'")
        classes_value = body.get("classes")
        if classes_value is not None:
            if not isinstance(classes_value, list):
                classes_value = [classes_value]
            for cls in classes_value:
                try:
                    CasterClass(str(cls))
                except Exception:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid value in 'classes'")

    spell.id = None
    _compute_spell_derived_fields(spell)
    session.add(spell)
    session.commit()
    session.refresh(spell)
    # `body` already loaded above
    translations = body.get("translations") if isinstance(body, dict) else None

    if isinstance(translations, dict):
        for lang_code in ("ru", "en"):
            data = translations.get(lang_code)
            if isinstance(data, dict) and data.get("name") and data.get("description"):
                l = _select_language(lang_code)
                existing = session.exec(
                    select(SpellTranslation).where(
                        SpellTranslation.spell_id == spell.id,
                        SpellTranslation.lang == l,
                    )
                ).first()
                if existing is None:
                    session.add(
                        SpellTranslation(
                            spell_id=spell.id,
                            lang=l,
                            name=data["name"],
                            description=data["description"],
                        )
                    )
                else:
                    existing.name = data["name"]
                    existing.description = data["description"]
                    session.add(existing)
        session.commit()

    logger.info("Spell created", extra={"spell_id": spell.id})
    return spell


@router.put("/{spell_id}", response_model=Spell)
async def update_spell(
    spell_id: int,
    payload: Spell,
    lang: Optional[str] = None,
    request: Request = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> Spell:
    # Strict extra-fields and enums validation
    try:
        body = await request.json() if request is not None else {}
    except Exception:
        body = {}
    if isinstance(body, dict):
        allowed_keys = set(Spell.model_fields.keys()) | {"translations"}
        extra_keys = set(body.keys()) - allowed_keys
        if extra_keys:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unexpected fields: {sorted(extra_keys)}")
        school_value = body.get("school")
        if school_value is not None:
            try:
                SpellSchool(str(school_value))
            except Exception:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid value for 'school'")
        classes_value = body.get("classes")
        if classes_value is not None:
            if not isinstance(classes_value, list):
                classes_value = [classes_value]
            for cls in classes_value:
                try:
                    CasterClass(str(cls))
                except Exception:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid value in 'classes'")

    spell = session.get(Spell, spell_id)
    if spell is None:
        logger.warning("Spell not found for update", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    spell.school = payload.school
    if payload.level is not None:
        spell.level = payload.level
    if payload.ritual is not None:
        spell.ritual = payload.ritual
    if payload.casting_time is not None:
        spell.casting_time = payload.casting_time
    if payload.range is not None:
        spell.range = payload.range
    if payload.duration is not None:
        spell.duration = payload.duration
    if payload.components is not None:
        spell.components = payload.components
    if payload.classes is not None:
        spell.classes = payload.classes
    if payload.damage is not None:
        spell.damage = payload.damage
    if payload.saving_throw is not None:
        spell.saving_throw = payload.saving_throw
    if payload.area is not None:
        spell.area = payload.area
    if payload.conditions is not None:
        spell.conditions = payload.conditions
    if payload.tags is not None:
        spell.tags = payload.tags
    _compute_spell_derived_fields(spell)
    session.add(spell)
    session.commit()
    session.refresh(spell)

    try:
        body = await request.json() if request is not None else {}
    except Exception:
        body = {}
    translations = body.get("translations") if isinstance(body, dict) else None

    if isinstance(translations, dict):
        for lang_code in ("ru", "en"):
            data = translations.get(lang_code)
            if isinstance(data, dict) and data.get("name") and data.get("description"):
                l = _select_language(lang_code)
                existing = session.exec(
                    select(SpellTranslation).where(
                        SpellTranslation.spell_id == spell.id,
                        SpellTranslation.lang == l,
                    )
                ).first()
                if existing is None:
                    session.add(
                        SpellTranslation(
                            spell_id=spell.id,
                            lang=l,
                            name=data["name"],
                            description=data["description"],
                        )
                    )
                else:
                    existing.name = data["name"]
                    existing.description = data["description"]
                    session.add(existing)
        session.commit()

    logger.info("Spell updated", extra={"spell_id": spell.id})
    return spell


@router.delete("/{spell_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spell(
    spell_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> None:
    spell = session.get(Spell, spell_id)
    if spell is None:
        logger.warning("Spell not found for delete", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")
    session.exec(delete(SpellTranslation).where(SpellTranslation.spell_id == spell_id))
    session.delete(spell)
    session.commit()
    logger.info("Spell deleted", extra={"spell_id": spell_id})
    return None


class SpellTranslationUpsert(BaseModel):
    lang: str
    name: str
    description: str


@router.post("/{spell_id}/translations", status_code=status.HTTP_204_NO_CONTENT)
def upsert_spell_translation(
    spell_id: int,
    body: SpellTranslationUpsert,
    session: Session = Depends(get_session),  # noqa: B008
) -> None:
    spell = session.get(Spell, spell_id)
    if spell is None:
        logger.warning("Spell not found for translation upsert", extra={"spell_id": spell_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spell not found")

    lang = _select_language(body.lang)

    existing = session.exec(
        select(SpellTranslation).where(
            SpellTranslation.spell_id == spell_id,
            SpellTranslation.lang == lang,
        )
    ).first()

    if existing is None:
        tr = SpellTranslation(
            spell_id=spell_id,
            lang=lang,
            name=body.name,
            description=body.description,
        )
        session.add(tr)
    else:
        existing.name = body.name
        existing.description = body.description
        session.add(existing)

    session.commit()
    logger.info(
        "Spell translation upserted",
        extra={"spell_id": spell_id, "lang": lang.value},
    )
    return None


