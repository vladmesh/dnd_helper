#!/usr/bin/env python3
"""
Script to update Russian translations in the monster_translations section.
Adds CLI parameters and repo-relative defaults for containerized runs.
"""

import json
import re
import argparse
import os


def normalize_name(name: str) -> str:
    """Нормализует название для сравнения"""
    if not name:
        return ""
    # Убираем лишние пробелы, приводим к нижнему регистру
    normalized = re.sub(r'\s+', ' ', name.strip().lower())
    # Normalize Cyrillic yo to ye for robust matching (e -> yo variants)
    normalized = normalized.replace('ё', 'е')
    # Убираем специальные символы и маркеры
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized


def load_data(seed_in_path: str, parsed_in_path: str):
    """Загружает данные из файлов"""
    try:
        print("📥 Загружаю исходный JSON файл...")
        with open(seed_in_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)

        print("📥 Загружаю спарсенные данные...")
        with open(parsed_in_path, 'r', encoding='utf-8') as f:
            parsed_data = json.load(f)

        monsters = parsed_data.get('monsters', []) if isinstance(parsed_data, dict) else parsed_data
        return original_data, monsters
    except Exception as e:
        print(f"❌ Ошибка загрузки данных: {e}")
        return None, None


def find_empty_russian_translations(original_data):
    """Находит русские переводы с пустыми описаниями"""
    monster_translations = original_data.get('monster_translations', [])
    empty_translations = []

    for i, translation in enumerate(monster_translations):
        if translation.get('lang') == 'ru':
            description = translation.get('description', '')
            if not description or description.strip() == '':
                empty_translations.append({
                    'index': i,
                    'monster_slug': translation.get('monster_slug', ''),
                    'name': translation.get('name', ''),
                    'translation': translation
                })

    return empty_translations


def build_en_name_by_slug(original_data):
    """Строит словарь monster_slug -> english name из seed (lang='en')."""
    en_by_slug = {}
    for t in original_data.get('monster_translations', []):
        if t.get('lang') == 'en':
            slug = t.get('monster_slug')
            name = t.get('name')
            if slug and name:
                en_by_slug[slug] = name
    return en_by_slug


def find_matches(empty_translations, parsed_monsters, en_name_by_slug=None):
    """Находит соответствия между пустыми переводами и спарсенными монстрами"""
    matches = []
    en_name_by_slug = en_name_by_slug or {}

    for empty_trans in empty_translations:
        empty_name_norm = normalize_name(empty_trans['name'])
        empty_slug = empty_trans['monster_slug']
        seed_en_norm = normalize_name(en_name_by_slug.get(empty_slug, '')) if empty_slug else ''

        for parsed_monster in parsed_monsters:
            parsed_name_norm = normalize_name(parsed_monster.get('name', ''))
            parsed_english_norm = normalize_name(parsed_monster.get('english_name', ''))

            # Ищем совпадения по названию
            if (
                (empty_name_norm and parsed_name_norm and empty_name_norm == parsed_name_norm) or
                (empty_name_norm and parsed_english_norm and empty_name_norm == parsed_english_norm) or
                (seed_en_norm and parsed_name_norm and seed_en_norm == parsed_name_norm) or
                (seed_en_norm and parsed_english_norm and seed_en_norm == parsed_english_norm)
            ):
                matches.append({
                    'empty_translation': empty_trans,
                    'parsed_monster': parsed_monster
                })
                print(f"🎯 Найдено совпадение: {empty_trans['name']} ({empty_slug}) ← {parsed_monster.get('name', '')}")
                break

    return matches


def update_translations(original_data, matches, replace_english_names=True):
    """Обновляет переводы в данных"""
    if not matches:
        print("ℹ️ Нет совпадений для обновления")
        return 0

    updated_count = 0

    for match in matches:
        empty_trans = match['empty_translation']
        parsed_monster = match['parsed_monster']
        index = empty_trans['index']

        # Обновляем описание
        new_description = parsed_monster.get('description', '')
        if new_description:
            original_data['monster_translations'][index]['description'] = new_description
            updated_count += 1
            print(f"✅ Обновлено описание для: {empty_trans['name']} ({empty_trans['monster_slug']})")

        # Обновляем название, если нужно (если текущее английское)
        current_name = empty_trans['name']
        parsed_name = parsed_monster.get('name', '')
        if replace_english_names and parsed_name and parsed_name != current_name:
            # Проверяем, не является ли текущее название английским
            if not re.search(r'[а-яё]', current_name.lower()):
                original_data['monster_translations'][index]['name'] = parsed_name
                print(f"✅ Обновлено название: {current_name} → {parsed_name}")

    return updated_count


def save_updated_data(data, output_path):
    """Сохраняет обновленные данные"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Обновленные данные сохранены в: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False


def main():
    print("🚀 Обновление русских переводов монстров")
    print("=" * 50)

    parser = argparse.ArgumentParser(description="Update Russian translations in monster_translations using parsed data")
    parser.add_argument('--seed-in', default='/app/seed_data_monsters.json', help='Path to input seed JSON')
    parser.add_argument('--seed-out', default='/app/seed_data_monsters_updated.json', help='Path to output updated seed JSON')
    parser.add_argument('--parsed-in', default='/app/scripts/monster_parser/output/parsed_monsters_filtered_final.json', help='Path to parsed monsters JSON')
    parser.add_argument('--replace-english-names', action='store_true', default=True, help='Replace English names with Russian if detected')
    parser.add_argument('--no-replace-english-names', dest='replace_english_names', action='store_false')
    parser.add_argument('--dry-run', action='store_true', help='Do not write output, only report')
    args = parser.parse_args()

    # Загружаем данные
    original_data, parsed_monsters = load_data(args.seed_in, args.parsed_in)
    if not original_data or not parsed_monsters:
        return

    print(f"📊 Загружено {len(parsed_monsters)} спарсенных монстров")

    # Находим пустые русские переводы
    empty_translations = find_empty_russian_translations(original_data)
    print(f"🔍 Найдено {len(empty_translations)} русских переводов с пустыми описаниями")

    if not empty_translations:
        print("ℹ️ Нет переводов для обновления")
        return

    # Показываем первые несколько примеров
    print("\n📋 Примеры пустых переводов:")
    for i, trans in enumerate(empty_translations[:10]):
        print(f"{i+1}. {trans['name']} ({trans['monster_slug']})")

    if len(empty_translations) > 10:
        print(f"... и еще {len(empty_translations) - 10} записей")

    # Фолбек: английские имена из seed по slug
    en_by_slug = build_en_name_by_slug(original_data)

    # Находим совпадения
    print("\n🔍 Поиск совпадений...")
    matches = find_matches(empty_translations, parsed_monsters, en_name_by_slug=en_by_slug)
    print(f"🎯 Найдено {len(matches)} совпадений для обновления")

    if not matches:
        print("ℹ️ Нет совпадений для обновления")
        return

    # Обновляем данные
    updated_count = update_translations(original_data, matches, replace_english_names=args.replace_english_names)

    if updated_count > 0:
        if args.dry_run:
            print(f"\n✅ (dry-run) Было бы обновлено {updated_count} переводов, файл не записан")
            return
        if save_updated_data(original_data, args.seed_out):
            print(f"\n✅ Успешно обновлено {updated_count} переводов!")
        else:
            print("\n❌ Ошибка сохранения обновленных данных")
    else:
        print("\nℹ️ Нет данных для сохранения")


if __name__ == "__main__":
    main()

