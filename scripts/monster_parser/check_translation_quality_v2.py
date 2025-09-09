#!/usr/bin/env python3
import json
import re
import argparse
import os

def has_cyrillic(text):
    """Проверяет, содержит ли текст кириллические символы"""
    if not text or not isinstance(text, str):
        return False
    return bool(re.search('[а-яё]', text.lower()))

def is_valid_russian_translation(text, field_name):
    """Проверяет, является ли текст корректным русским переводом"""
    if not text or not isinstance(text, str):
        return False, f"Пустое поле {field_name}"
    
    text = text.strip()
    if not text:
        return False, f"Пустое поле {field_name} (только пробелы)"
    
    if not has_cyrillic(text):
        return False, f"Нет кириллических символов в {field_name}"
    
    # Проверяем на явно английские слова
    english_patterns = [
        r'^[A-Z][a-z]+ is a ',  # "Dragon is a Large..."
        r'^[A-Z][a-z]+ are ',   # "Goblins are Small..."
        r'^\w+ \w+ Attack:',    # "Melee Weapon Attack:"
        r'Hit: \d+',            # "Hit: 15"
        r'DC \d+',              # "DC 14"
        r'^Adult [A-Z]',        # "Adult Black Dragon"
        r'^Ancient [A-Z]',      # "Ancient Red Dragon"
        r'^Young [A-Z]',        # "Young Blue Dragon"
    ]
    
    for pattern in english_patterns:
        if re.search(pattern, text):
            return False, f"Содержит английский текст в {field_name}"
    
    # Проверяем процент английских символов
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    total_chars = len(re.sub(r'[^а-яёa-zA-Z]', '', text))
    
    if total_chars > 0 and (english_chars / total_chars) > 0.3:  # Если больше 30% английских символов
        return False, f"Слишком много английских символов в {field_name}"
    
    return True, "OK"

def analyze_translation_quality(seed_in_path: str, lang: str, report_dir: str, english_ratio_threshold: float):
    """Анализирует качество русских переводов"""
    with open(seed_in_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    translations = data.get('monster_translations', [])
    
    print(f"Анализ качества переводов для {len(translations)} записей")
    print("=" * 60)
    
    # Фильтруем только целевой язык
    russian_translations = [t for t in translations if t.get('lang') == lang]
    print(f"Русских переводов: {len(russian_translations)}")
    print()
    
    # Анализируем качество
    problems = {
        'name': [],
        'description': []
    }
    
    valid_translations = 0
    
    for translation in russian_translations:
        slug = translation.get('monster_slug', 'unknown')
        name = translation.get('name', '')
        description = translation.get('description', '')
        
        has_problems = False
        
        # Проверяем название
        name_valid, name_issue = is_valid_russian_translation(name, 'name')
        if not name_valid:
            problems['name'].append({
                'slug': slug,
                'issue': name_issue,
                'content': name[:100] + '...' if len(name) > 100 else name
            })
            has_problems = True
        
        # Проверяем описание
        desc_valid, desc_issue = is_valid_russian_translation(description, 'description')
        if not desc_valid:
            problems['description'].append({
                'slug': slug,
                'issue': desc_issue,
                'content': description[:100] + '...' if len(description) > 100 else description
            })
            has_problems = True
        
        if not has_problems:
            valid_translations += 1
    
    # Выводим статистику
    print(f"Корректных переводов: {valid_translations}")
    print(f"Проблем с названиями: {len(problems['name'])}")
    print(f"Проблем с описаниями: {len(problems['description'])}")
    print()
    
    # Показываем примеры проблем
    if problems['name']:
        print("Примеры проблем с названиями (первые 10):")
        for i, problem in enumerate(problems['name'][:10]):
            print(f"  {i+1}. {problem['slug']}: {problem['issue']}")
            print(f"      Содержимое: '{problem['content']}'")
        print()
    
    if problems['description']:
        print("Примеры проблем с описаниями (первые 10):")
        for i, problem in enumerate(problems['description'][:10]):
            print(f"  {i+1}. {problem['slug']}: {problem['issue']}")
            print(f"      Содержимое: '{problem['content']}'")
        print()
    
    # Сохраняем полные списки проблем
    os.makedirs(report_dir, exist_ok=True)
    with open(os.path.join(report_dir, 'problems_with_names_v2.txt'), 'w', encoding='utf-8') as f:
        f.write("Проблемы с русскими названиями монстров:\n")
        f.write("=" * 50 + "\n\n")
        for problem in problems['name']:
            f.write(f"Slug: {problem['slug']}\n")
            f.write(f"Проблема: {problem['issue']}\n")
            f.write(f"Содержимое: {problem['content']}\n")
            f.write("-" * 30 + "\n")
    
    with open(os.path.join(report_dir, 'problems_with_descriptions_v2.txt'), 'w', encoding='utf-8') as f:
        f.write("Проблемы с русскими описаниями монстров:\n")
        f.write("=" * 50 + "\n\n")
        for problem in problems['description']:
            f.write(f"Slug: {problem['slug']}\n")
            f.write(f"Проблема: {problem['issue']}\n")
            f.write(f"Содержимое: {problem['content']}\n")
            f.write("-" * 30 + "\n")
    
    print(f"Детальные списки проблем сохранены в файлы:")
    print(f"  - problems_with_names_v2.txt ({len(problems['name'])} записей)")
    print(f"  - problems_with_descriptions_v2.txt ({len(problems['description'])} записей)")
    
    # Статистика качества
    total_fields = len(russian_translations) * 2  # name + description
    problem_fields = len(problems['name']) + len(problems['description'])
    quality_percentage = ((total_fields - problem_fields) / total_fields) * 100
    
    print(f"\nОбщая статистика качества переводов: {quality_percentage:.1f}%")
    print(f"Полей требующих исправления: {problem_fields} из {total_fields}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze quality of translations in seed data")
    parser.add_argument('--seed-in', default='/app/seed_data_monsters.json', help='Path to seed JSON')
    parser.add_argument('--lang', default='ru', help='Language to analyze')
    parser.add_argument('--report-dir', default='/app/scripts/monster_parser/output/reports', help='Directory to write reports')
    parser.add_argument('--english-ratio-threshold', type=float, default=0.3, help='Max allowed share of Latin letters')
    args = parser.parse_args()

    analyze_translation_quality(args.seed_in, args.lang, args.report_dir, args.english_ratio_threshold)

