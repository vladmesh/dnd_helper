from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import delete
from sqlmodel import Session, select

from dnd_helper_api.db import get_session
from dnd_helper_api.routers.monsters import router, logger
from shared_models import Monster
from shared_models.monster_translation import MonsterTranslation

from .derived import _compute_monster_derived_fields
from .translations import _apply_monster_translation, _select_language


@router.post("", response_model=Monster, status_code=status.HTTP_201_CREATED)
async def create_monster(
    monster: Monster,
    lang: Optional[str] = None,
    request: Request = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> Monster:
    monster.id = None
    _compute_monster_derived_fields(monster)
    session.add(monster)
    session.commit()
    session.refresh(monster)
    try:
        body = await request.json() if request is not None else {}
    except Exception:
        body = {}
    translations = body.get("translations") if isinstance(body, dict) else None

    if isinstance(translations, dict):
        for lang_code in ("ru", "en"):
            data = translations.get(lang_code)
            if isinstance(data, dict) and (data.get("name") and data.get("description") or any(k in data for k in ("traits","actions","reactions","legendary_actions","spellcasting"))):
                l = _select_language(lang_code)
                existing = session.exec(
                    select(MonsterTranslation).where(
                        MonsterTranslation.monster_id == monster.id,
                        MonsterTranslation.lang == l,
                    )
                ).first()
                if existing is None:
                    session.add(
                        MonsterTranslation(
                            monster_id=monster.id,
                            lang=l,
                            name=(data.get("name") or ""),
                            description=(data.get("description") if data.get("description") is not None else ""),
                            traits=data.get("traits"),
                            actions=data.get("actions"),
                            reactions=data.get("reactions"),
                            legendary_actions=data.get("legendary_actions"),
                            spellcasting=data.get("spellcasting"),
                        )
                    )
                else:
                    if data.get("name"):
                        existing.name = data["name"]
                    if data.get("description"):
                        existing.description = data["description"]
                    existing.traits = data.get("traits")
                    existing.actions = data.get("actions")
                    existing.reactions = data.get("reactions")
                    existing.legendary_actions = data.get("legendary_actions")
                    existing.spellcasting = data.get("spellcasting")
                    session.add(existing)
        session.commit()

    logger.info("Monster created", extra={"monster_id": monster.id})
    return monster


@router.put("/{monster_id}", response_model=Monster)
async def update_monster(
    monster_id: int,
    payload: Monster,
    lang: Optional[str] = None,
    request: Request = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> Monster:
    monster = session.get(Monster, monster_id)
    if monster is None:
        logger.warning("Monster not found for update", extra={"monster_id": monster_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    monster.hp = payload.hp
    monster.ac = payload.ac
    if payload.type is not None:
        monster.type = payload.type
    if payload.size is not None:
        monster.size = payload.size
    if payload.alignment is not None:
        monster.alignment = payload.alignment
    if payload.hit_dice is not None:
        monster.hit_dice = payload.hit_dice
    if payload.cr is not None:
        monster.cr = payload.cr
    if payload.xp is not None:
        monster.xp = payload.xp
    if payload.proficiency_bonus is not None:
        monster.proficiency_bonus = payload.proficiency_bonus
    if payload.abilities is not None:
        monster.abilities = payload.abilities
    if payload.saving_throws is not None:
        monster.saving_throws = payload.saving_throws
    if payload.skills is not None:
        monster.skills = payload.skills
    if payload.senses is not None:
        monster.senses = payload.senses
    if payload.languages is not None:
        monster.languages = payload.languages
    if payload.damage_immunities is not None:
        monster.damage_immunities = payload.damage_immunities
    if payload.damage_resistances is not None:
        monster.damage_resistances = payload.damage_resistances
    if payload.damage_vulnerabilities is not None:
        monster.damage_vulnerabilities = payload.damage_vulnerabilities
    if payload.condition_immunities is not None:
        monster.condition_immunities = payload.condition_immunities
    if payload.tags is not None:
        monster.tags = payload.tags
    _compute_monster_derived_fields(monster)
    session.add(monster)
    session.commit()
    session.refresh(monster)

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
                    select(MonsterTranslation).where(
                        MonsterTranslation.monster_id == monster.id,
                        MonsterTranslation.lang == l,
                    )
                ).first()
                if existing is None:
                    session.add(
                        MonsterTranslation(
                            monster_id=monster.id,
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

    logger.info("Monster updated", extra={"monster_id": monster.id})
    return monster


@router.delete("/{monster_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monster(
    monster_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> None:
    monster = session.get(Monster, monster_id)
    if monster is None:
        logger.warning("Monster not found for delete", extra={"monster_id": monster_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")
    session.exec(delete(MonsterTranslation).where(MonsterTranslation.monster_id == monster_id))
    session.delete(monster)
    session.commit()
    logger.info("Monster deleted", extra={"monster_id": monster.id if monster else monster_id})
    return None


class MonsterTranslationUpsert(BaseModel):
    lang: str
    name: str
    description: str


@router.post("/{monster_id}/translations", status_code=status.HTTP_204_NO_CONTENT)
def upsert_monster_translation(
    monster_id: int,
    body: MonsterTranslationUpsert,
    session: Session = Depends(get_session),  # noqa: B008
) -> None:
    monster = session.get(Monster, monster_id)
    if monster is None:
        logger.warning("Monster not found for translation upsert", extra={"monster_id": monster_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monster not found")

    lang = _select_language(body.lang)

    existing = session.exec(
        select(MonsterTranslation).where(
            MonsterTranslation.monster_id == monster_id,
            MonsterTranslation.lang == lang,
        )
    ).first()

    if existing is None:
        tr = MonsterTranslation(
            monster_id=monster_id,
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
        "Monster translation upserted",
        extra={"monster_id": monster_id, "lang": lang.value},
    )
    return None


