#!/usr/bin/env python3
import json
from collections import Counter
import glob
import argparse
import os

def analyze_sources(parsed_files):
    """Анализирует источники из уже спарсенных данных"""
    
    all_sources = Counter()
    all_monsters = []
    
    for file_path in parsed_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                monsters = data.get('monsters', [])
                all_monsters.extend(monsters)
                
                for monster in monsters:
                    source = monster.get('source', 'Unknown')
                    all_sources[source] += 1
                    
        except FileNotFoundError:
            continue
    
    print(f"📊 Анализ источников из {len(all_monsters)} спарсенных монстров:")
    print("=" * 50)
    
    # Определяем Core источники (основные книги D&D 5e)
    core_sources = {
        'MM': 'Monster Manual',
        'PHB': "Player's Handbook", 
        'DMG': "Dungeon Master's Guide",
        '': 'Basic Rules (без источника)'  # Базовые правила
    }
    
    print("🎯 CORE источники (основные книги):")
    core_count = 0
    for source_code, source_name in core_sources.items():
        count = all_sources.get(source_code, 0)
        core_count += count
        print(f"  {source_code or 'Пусто'}: {count} монстров ({source_name})")
    
    print(f"\n📚 Все остальные источники:")
    other_count = 0
    for source, count in all_sources.most_common():
        if source not in core_sources:
            other_count += count
            print(f"  {source}: {count} монстров")
    
    print(f"\n📈 Статистика:")
    print(f"  Core монстры: {core_count}")
    print(f"  Остальные: {other_count}")
    print(f"  Всего: {len(all_monsters)}")
    print(f"  Процент Core: {(core_count/len(all_monsters)*100):.1f}%")
    
    return core_sources, all_monsters

def create_core_filter():
    """Создает список Core источников для фильтрации"""
    
    # Основные источники D&D 5e (Core)
    core_sources = {
        'MM',      # Monster Manual
        'PHB',     # Player's Handbook
        'DMG',     # Dungeon Master's Guide
        '',        # Basic Rules (без указания источника)
        'SRD'      # System Reference Document (если есть)
    }
    
    print("✅ Core источники для фильтрации:")
    for source in sorted(core_sources):
        print(f"  - '{source}'")
    
    return core_sources

if __name__ == "__main__":
    print("🔍 Анализ источников монстров")
    print("=" * 40)

    parser = argparse.ArgumentParser(description="Analyze sources from parsed monsters batches")
    parser.add_argument('--inputs', default='/app/scripts/monster_parser/output/parsed_monsters_filtered_batch_*.json', help='Glob pattern for parsed batch files')
    parser.add_argument('--final', default='', help='Optional final parsed file to include')
    parser.add_argument('--report-out', default='/app/scripts/monster_parser/output/reports/sources.json', help='Report output JSON path')
    args = parser.parse_args()

    files = sorted(glob.glob(args.inputs))
    if args.final:
        files.append(args.final)

    os.makedirs(os.path.dirname(args.report_out), exist_ok=True)

    core_sources, monsters = analyze_sources(files)

    print("\n" + "=" * 40)

    filter_sources = create_core_filter()

    with open(args.report_out, 'w', encoding='utf-8') as f:
        json.dump({
            'core_sources': list(filter_sources),
            'total_monsters': len(monsters)
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Отчет об источниках сохранен: {args.report_out}")

