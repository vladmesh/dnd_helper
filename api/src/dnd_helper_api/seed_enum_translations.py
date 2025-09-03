from __future__ import annotations

from typing import Dict, List, Tuple

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session

from dnd_helper_api.db import engine
from shared_models.enum_translation import EnumTranslation
from shared_models.ui_translation import UiTranslation


def build_rows() -> List[Dict[str, str]]:
    """Build seed rows for enum_translations (RU/EN labels)."""
    rows: List[Dict[str, str]] = []

    # spell_school
    schools: List[Tuple[str, str, str]] = [
        ("abjuration", "ru", "Ограждение"),
        ("conjuration", "ru", "Воплощение"),
        ("divination", "ru", "Прорицание"),
        ("enchantment", "ru", "Очарование"),
        ("evocation", "ru", "Эвокация"),
        ("illusion", "ru", "Иллюзия"),
        ("necromancy", "ru", "Некромантия"),
        ("transmutation", "ru", "Трансмутация"),
        ("abjuration", "en", "Abjuration"),
        ("conjuration", "en", "Conjuration"),
        ("divination", "en", "Divination"),
        ("enchantment", "en", "Enchantment"),
        ("evocation", "en", "Evocation"),
        ("illusion", "en", "Illusion"),
        ("necromancy", "en", "Necromancy"),
        ("transmutation", "en", "Transmutation"),
    ]
    rows.extend(
        {
            "enum_type": "spell_school",
            "enum_value": code,
            "lang": lang,
            "label": label,
        }
        for code, lang, label in schools
    )

    # caster_class
    classes: List[Tuple[str, str, str]] = [
        ("wizard", "ru", "Маг"),
        ("sorcerer", "ru", "Чародей"),
        ("cleric", "ru", "Жрец"),
        ("druid", "ru", "Друид"),
        ("paladin", "ru", "Паладин"),
        ("ranger", "ru", "Следопыт"),
        ("bard", "ru", "Бард"),
        ("warlock", "ru", "Колдун"),
        ("wizard", "en", "Wizard"),
        ("sorcerer", "en", "Sorcerer"),
        ("cleric", "en", "Cleric"),
        ("druid", "en", "Druid"),
        ("paladin", "en", "Paladin"),
        ("ranger", "en", "Ranger"),
        ("bard", "en", "Bard"),
        ("warlock", "en", "Warlock"),
    ]
    rows.extend(
        {
            "enum_type": "caster_class",
            "enum_value": code,
            "lang": lang,
            "label": label,
        }
        for code, lang, label in classes
    )

    # monster_size
    sizes: List[Tuple[str, str, str]] = [
        ("tiny", "ru", "Крошечный"),
        ("small", "ru", "Маленький"),
        ("medium", "ru", "Средний"),
        ("large", "ru", "Большой"),
        ("huge", "ru", "Огромный"),
        ("gargantuan", "ru", "Громадный"),
        ("tiny", "en", "Tiny"),
        ("small", "en", "Small"),
        ("medium", "en", "Medium"),
        ("large", "en", "Large"),
        ("huge", "en", "Huge"),
        ("gargantuan", "en", "Gargantuan"),
    ]
    rows.extend(
        {
            "enum_type": "monster_size",
            "enum_value": code,
            "lang": lang,
            "label": label,
        }
        for code, lang, label in sizes
    )

    # monster_type
    types_: List[Tuple[str, str, str]] = [
        ("aberration", "ru", "Аберрация"),
        ("beast", "ru", "Зверь"),
        ("celestial", "ru", "Небожитель"),
        ("construct", "ru", "Конструкт"),
        ("dragon", "ru", "Дракон"),
        ("elemental", "ru", "Элементаль"),
        ("fey", "ru", "Фея"),
        ("fiend", "ru", "Исчадие"),
        ("giant", "ru", "Великан"),
        ("humanoid", "ru", "Гуманоид"),
        ("monstrosity", "ru", "Чудовище"),
        ("ooze", "ru", "Слизь"),
        ("plant", "ru", "Растение"),
        ("undead", "ru", "Нежить"),
        ("aberration", "en", "Aberration"),
        ("beast", "en", "Beast"),
        ("celestial", "en", "Celestial"),
        ("construct", "en", "Construct"),
        ("dragon", "en", "Dragon"),
        ("elemental", "en", "Elemental"),
        ("fey", "en", "Fey"),
        ("fiend", "en", "Fiend"),
        ("giant", "en", "Giant"),
        ("humanoid", "en", "Humanoid"),
        ("monstrosity", "en", "Monstrosity"),
        ("ooze", "en", "Ooze"),
        ("plant", "en", "Plant"),
        ("undead", "en", "Undead"),
    ]
    rows.extend(
        {
            "enum_type": "monster_type",
            "enum_value": code,
            "lang": lang,
            "label": label,
        }
        for code, lang, label in types_
    )

    # danger_level (Challenge Rating labels mirror codes)
    cr_values = ["1/8", "1/4", "1/2"] + [str(i) for i in range(1, 31)]
    for code in cr_values:
        rows.append({"enum_type": "danger_level", "enum_value": code, "lang": "ru", "label": code})
        rows.append({"enum_type": "danger_level", "enum_value": code, "lang": "en", "label": code})

    return rows


def upsert_rows(rows: List[Dict[str, str]]) -> None:
    """Upsert rows using PostgreSQL ON CONFLICT on (enum_type, enum_value, lang)."""
    table = EnumTranslation.__table__
    stmt = pg_insert(table).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[table.c.enum_type, table.c.enum_value, table.c.lang],
        set_={"label": stmt.excluded.label},
    )

    with Session(engine) as session:
        session.exec(stmt)
        session.commit()


def build_ui_rows() -> List[Dict[str, str]]:
    """Build seed rows for ui_translations (bot namespace)."""
    ns = "bot"
    pairs: List[Tuple[str, str, str]] = [
        ("menu.main.title", "ru", "Главное меню"),
        ("menu.main.title", "en", "Main menu"),
        ("menu.bestiary.title", "ru", "Бестиарий"),
        ("menu.bestiary.title", "en", "Bestiary"),
        ("menu.spells.title", "ru", "Заклинания"),
        ("menu.spells.title", "en", "Spells"),
        ("menu.settings.title", "ru", "Настройки"),
        ("menu.settings.title", "en", "Settings"),
        ("dice.menu.title", "ru", "Бросить кубики"),
        ("dice.menu.title", "en", "Roll dice"),
        ("dice.custom.prompt.count", "ru", "Сколько кубиков бросить? (1-100)"),
        ("dice.custom.prompt.count", "en", "How many dice to roll? (1-100)"),
        ("dice.custom.prompt.faces", "ru", "Номинал кубика? (2,3,4,6,8,10,12,20,100)"),
        ("dice.custom.prompt.faces", "en", "Die faces? (2,3,4,6,8,10,12,20,100)"),
        ("dice.custom.error.range", "ru", "Количество должно быть от 1 до 100"),
        ("dice.custom.error.range", "en", "Count must be between 1 and 100"),
        ("dice.custom.error.allowed", "ru", "Разрешены только: 2,3,4,6,8,10,12,20,100"),
        ("dice.custom.error.allowed", "en", "Allowed only: 2,3,4,6,8,10,12,20,100"),
        ("monsters.search.prompt", "ru", "Введите подстроку для поиска по названию монстра:"),
        ("monsters.search.prompt", "en", "Enter substring to search monster by name:"),
        ("spells.search.prompt", "ru", "Введите подстроку для поиска по названию заклинания:"),
        ("spells.search.prompt", "en", "Enter substring to search spell by name:"),
        ("list.empty.monsters", "ru", "Монстров нет."),
        ("list.empty.monsters", "en", "No monsters."),
        ("list.empty.spells", "ru", "Заклинаний нет."),
        ("list.empty.spells", "en", "No spells."),
        ("nav.back", "ru", "⬅️ Назад"),
        ("nav.back", "en", "⬅️ Back"),
        ("nav.next", "ru", "➡️ Далее"),
        ("nav.next", "en", "➡️ Next"),
        ("nav.main", "ru", "К главному меню"),
        ("nav.main", "en", "Main menu"),
    ]
    return [{"namespace": ns, "key": k, "lang": lang, "text": text} for k, lang, text in pairs]


def upsert_ui_rows(rows: List[Dict[str, str]]) -> None:
    """Upsert ui_translations using ON CONFLICT (namespace,key,lang)."""
    table = UiTranslation.__table__
    stmt = pg_insert(table).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[table.c.namespace, table.c.key, table.c.lang],
        set_={"text": stmt.excluded.text},
    )

    with Session(engine) as session:
        session.exec(stmt)
        session.commit()


def main() -> None:
    rows = build_rows()
    upsert_rows(rows)
    ui_rows = build_ui_rows()
    upsert_ui_rows(ui_rows)


if __name__ == "__main__":
    main()


