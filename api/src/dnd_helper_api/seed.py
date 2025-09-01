from __future__ import annotations

from dnd_helper_api.db import engine
from sqlmodel import Session, select

from shared_models import CasterClass, DangerLevel, Monster, Spell, SpellSchool


def is_empty(session: Session, model: type) -> bool:
    return session.exec(select(model).limit(1)).first() is None


def seed_monsters(session: Session) -> None:
    if not is_empty(session, Monster):
        return

    monsters: list[Monster] = [
        Monster(
            title="Goblin",
            description="Goblin — small, sneaky humanoid.",
            dangerous_lvl=DangerLevel.LOW,
            hp=7,
            ac=15,
            speed=30,
        ),
        Monster(
            title="Orc",
            description="Orc — brutal warrior.",
            dangerous_lvl=DangerLevel.MODERATE,
            hp=15,
            ac=13,
            speed=30,
        ),
        Monster(
            title="Troll",
            description="Troll — regenerating giant.",
            dangerous_lvl=DangerLevel.HIGH,
            hp=84,
            ac=15,
            speed=30,
        ),
        Monster(
            title="Young Red Dragon",
            description="Young Red Dragon — fearsome dragon wyrmling.",
            dangerous_lvl=DangerLevel.DEADLY,
            hp=178,
            ac=18,
            speed=40,
        ),
    ]

    for m in monsters:
        session.add(m)
    session.commit()


def seed_spells(session: Session) -> None:
    if not is_empty(session, Spell):
        return

    spells: list[Spell] = [
        Spell(
            title="Fire Bolt",
            description="Fire Bolt — a mote of fire that deals damage.",
            school=SpellSchool.EVOCATION,
            classes=[CasterClass.WIZARD],
        ),
        Spell(
            title="Cure Wounds",
            description="Cure Wounds — touch to restore hit points.",
            school=SpellSchool.EVOCATION,
            classes=[CasterClass.CLERIC],
        ),
        Spell(
            title="Mage Hand",
            description="Mage Hand — spectral hand to manipulate objects.",
            school=SpellSchool.CONJURATION,
            classes=[CasterClass.SORCERER],
        ),
        Spell(
            title="Fireball",
            description="Fireball — explosive fire dealing area damage.",
            school=SpellSchool.EVOCATION,
            classes=[CasterClass.WIZARD],
        ),
    ]

    for s in spells:
        session.add(s)
    session.commit()


def main() -> None:
    with Session(engine) as session:
        seed_monsters(session)
        seed_spells(session)


if __name__ == "__main__":
    main()


