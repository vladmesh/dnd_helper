from __future__ import annotations

import argparse
import json
import os
from typing import Any, List, Optional

from .http import curl_get_json, curl_post_json
from .container import upsert_enum_and_ui_translations_in_container
from .builders import (
    build_monster_payloads_from_seed,
    build_spell_payloads_from_seed,
    build_enum_rows_from_seed,
    build_ui_rows_from_seed,
)


def _default_ui_pairs() -> List[tuple[str, str, str]]:
    return [
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
        ("dice.quick.d20", "ru", "d20"),
        ("dice.quick.d20", "en", "d20"),
        ("dice.quick.d6", "ru", "d6"),
        ("dice.quick.d6", "en", "d6"),
        ("dice.quick.2d6", "ru", "2d6"),
        ("dice.quick.2d6", "en", "2d6"),
        ("dice.custom.button", "ru", "Произвольный бросок"),
        ("dice.custom.button", "en", "Custom roll"),
        ("dice.custom.prompt.count", "ru", "Сколько кубиков бросить? (1-100)"),
        ("dice.custom.prompt.count", "en", "How many dice to roll? (1-100)"),
        ("dice.custom.prompt.faces", "ru", "Номинал кубика? (2,3,4,6,8,10,12,20,100)"),
        ("dice.custom.prompt.faces", "en", "Die faces? (2,3,4,6,8,10,12,20,100)"),
        ("dice.custom.error.range", "ru", "Количество должно быть от 1 до 100"),
        ("dice.custom.error.range", "en", "Count must be between 1 and 100"),
        ("dice.custom.error.allowed", "ru", "Разрешены только: 2,3,4,6,8,10,12,20,100"),
        ("dice.custom.error.allowed", "en", "Allowed only: 2,3,4,6,8,10,12,20,100"),
        ("dice.unknown", "ru", "Неизвестный бросок"),
        ("dice.unknown", "en", "Unknown roll"),
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
        # Newly added keys for de-hardcoding bot UI
        ("settings.lang.ru", "ru", "Русский"),
        ("settings.lang.ru", "en", "Русский"),
        ("settings.lang.en", "ru", "English"),
        ("settings.lang.en", "en", "English"),
        ("label.cr", "ru", "ОВ"),
        ("label.cr", "en", "CR"),
        ("label.hp", "ru", "ОЗ"),
        ("label.hp", "en", "HP"),
        ("label.ac", "ru", "КД"),
        ("label.ac", "en", "AC"),
        ("label.random_suffix", "ru", " (случайно)"),
        ("label.random_suffix", "en", " (random)"),
        ("spells.detail.classes", "ru", "Классы"),
        ("spells.detail.classes", "en", "Classes"),
        ("spells.detail.school", "ru", "Школа"),
        ("spells.detail.school", "en", "School"),
        ("filters.legendary", "ru", "Легендарный"),
        ("filters.legendary", "en", "Legendary"),
        ("filters.flying", "ru", "Летающий"),
        ("filters.flying", "en", "Flying"),
        ("filters.cr.03", "ru", "ОВ 0-3"),
        ("filters.cr.03", "en", "CR 0-3"),
        ("filters.cr.48", "ru", "ОВ 4-8"),
        ("filters.cr.48", "en", "CR 4-8"),
        ("filters.cr.9p", "ru", "ОВ 9+"),
        ("filters.cr.9p", "en", "CR 9+"),
        ("filters.size.S", "ru", "Размер S"),
        ("filters.size.S", "en", "Size S"),
        ("filters.size.M", "ru", "Размер M"),
        ("filters.size.M", "en", "Size M"),
        ("filters.size.L", "ru", "Размер L"),
        ("filters.size.L", "en", "Size L"),
        ("filters.ritual", "ru", "Ритуал"),
        ("filters.ritual", "en", "Ritual"),
        ("filters.concentration", "ru", "Концентрация"),
        ("filters.concentration", "en", "Concentration"),
        ("filters.cast.bonus", "ru", "Бонус"),
        ("filters.cast.bonus", "en", "Bonus"),
        ("filters.cast.reaction", "ru", "Реакция"),
        ("filters.cast.reaction", "en", "Reaction"),
        ("filters.level.13", "ru", "Ур 1-3"),
        ("filters.level.13", "en", "Lv 1-3"),
        ("filters.level.45", "ru", "Ур 4-5"),
        ("filters.level.45", "en", "Lv 4-5"),
        ("filters.level.69", "ru", "Ур 6-9"),
        ("filters.level.69", "en", "Lv 6-9"),
        ("filters.apply", "ru", "Применить"),
        ("filters.apply", "en", "Apply"),
        ("filters.reset", "ru", "Сброс"),
        ("filters.reset", "en", "Reset"),
        ("list.title.monsters", "ru", "Список монстров"),
        ("list.title.monsters", "en", "Monsters list"),
        ("list.title.spells", "ru", "Список заклинаний"),
        ("list.title.spells", "en", "Spells list"),
        ("label.more", "ru", "Подробнее:"),
        ("label.more", "en", "More:"),
        ("search.select_action", "ru", "Выберите действие:"),
        ("search.select_action", "en", "Choose an action:"),
        ("search.empty_query", "ru", "Пустой запрос. Повторите."),
        ("search.empty_query", "en", "Empty query. Repeat."),
        ("search.api_error", "ru", "Ошибка при запросе к API."),
        ("search.api_error", "en", "API request error."),
        ("search.no_results", "ru", "Ничего не найдено."),
        ("search.no_results", "en", "No results."),
        ("search.results_title", "ru", "Результаты поиска:"),
        ("search.results_title", "en", "Search results:"),
        ("settings.choose_language_prompt", "ru", "Выберите язык для начала"),
        ("settings.choose_language_prompt", "en", "Choose language first"),
        ("settings.error.save", "ru", "Ошибка сохранения настроек. Попробуйте ещё раз."),
        ("settings.error.save", "en", "Failed to save settings. Please try again."),
        # Root keyboards
        ("monsters.menu.list", "ru", "Список монстров"),
        ("monsters.menu.list", "en", "Monsters list"),
        ("monsters.menu.random", "ru", "Случайный монстр"),
        ("monsters.menu.random", "en", "Random monster"),
        ("monsters.menu.search", "ru", "Поиск монстра"),
        ("monsters.menu.search", "en", "Search monster"),
        ("spells.menu.list", "ru", "Список заклинаний"),
        ("spells.menu.list", "en", "Spells list"),
        ("spells.menu.random", "ru", "Случайное заклинание"),
        ("spells.menu.random", "en", "Random spell"),
        ("spells.menu.search", "ru", "Поиск заклинания"),
        ("spells.menu.search", "en", "Search spell"),
    ]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Seed data (monsters, spells, enums, ui) from seed JSON")
    parser.add_argument("--api-base-url", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--monsters", action="store_true", help="Import monsters")
    parser.add_argument("--spells", action="store_true", help="Import spells")
    parser.add_argument("--enums", action="store_true", help="Upsert enum translations")
    parser.add_argument("--ui", action="store_true", help="Upsert UI translations")
    parser.add_argument("--all", action="store_true", help="Do everything (monsters, spells, enums, ui)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of imported items per type")
    parser.add_argument("--dry-run", action="store_true", help="Do not POST, just show summary and samples")

    args = parser.parse_args(argv)

    if args.all:
        args.monsters = True
        args.spells = True
        args.enums = True
        args.ui = True
    if not any([args.monsters, args.spells, args.enums, args.ui]):
        args.monsters = True
        args.spells = True
        args.enums = True
        args.ui = True

    # API connectivity check (only needed if we touch monsters/spells)
    if args.monsters or args.spells:
        try:
            _ = curl_get_json(args.api_base_url, "/health")
        except SystemExit:
            print("API is not reachable at", args.api_base_url)
            return 1

    # Load seed JSON once (fixed path next to this CLI module)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    seed_path = os.path.join(os.path.dirname(script_dir), "seed_data.json")
    with open(seed_path, "r", encoding="utf-8") as f:
        seed = json.load(f)

    if args.monsters:
        monster_payloads = build_monster_payloads_from_seed(seed, limit=args.limit)
        print(f"Monsters prepared: {len(monster_payloads)}")
        if args.dry_run:
            for sample in monster_payloads[: min(3, len(monster_payloads))]:
                import json as _json
                body = _json.dumps(sample, ensure_ascii=False)
                print(body[:500] + ("..." if len(body) > 500 else ""))
        else:
            existing = curl_get_json(args.api_base_url, "/monsters") or []
            if existing:
                print(f"Monsters already present: {len(existing)}. Skipping import.")
            else:
                for idx, p in enumerate(monster_payloads, 1):
                    created = curl_post_json(args.api_base_url, "/monsters", p)
                    print(f"[{idx}/{len(monster_payloads)}] Created monster id={created.get('id')} name={created.get('name')}")

    if args.spells:
        spell_payloads = build_spell_payloads_from_seed(seed, limit=args.limit)
        print(f"Spells prepared: {len(spell_payloads)}")
        if args.dry_run:
            for sample in spell_payloads[: min(3, len(spell_payloads))]:
                import json as _json
                body = _json.dumps(sample, ensure_ascii=False)
                print(body[:500] + ("..." if len(body) > 500 else ""))
        else:
            existing = curl_get_json(args.api_base_url, "/spells") or []
            if existing:
                print(f"Spells already present: {len(existing)}. Skipping import.")
            else:
                for idx, p in enumerate(spell_payloads, 1):
                    created = curl_post_json(args.api_base_url, "/spells", p)
                    print(f"[{idx}/{len(spell_payloads)}] Created spell id={created.get('id')} name={created.get('name')}")

    if args.enums or args.ui:
        enum_rows = build_enum_rows_from_seed(seed) if args.enums else []
        ui_rows = build_ui_rows_from_seed(seed, _default_ui_pairs()) if args.ui else []
        print(f"Enum translations: {len(enum_rows)} | UI translations: {len(ui_rows)}")
        if not args.dry_run:
            upsert_enum_and_ui_translations_in_container(enum_rows, ui_rows)
        else:
            print("[dry-run] Skipping enum/ui upsert")

    return 0


