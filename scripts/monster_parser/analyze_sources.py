#!/usr/bin/env python3
import json
from collections import Counter

def analyze_sources():
    """Анализирует источники из уже спарсенных данных"""
    
    # Проверяем, какие источники уже есть в спарсенных данных
    parsed_files = [
        "/home/ubuntu/parsed_monsters_batch_1.json",
        "/home/ubuntu/parsed_monsters_batch_2.json", 
        "/home/ubuntu/parsed_monsters_batch_3.json",
        "/home/ubuntu/parsed_monsters_batch_4.json",
        "/home/ubuntu/parsed_monsters_batch_5.json",
        "/home/ubuntu/parsed_monsters_batch_6.json",
        "/home/ubuntu/parsed_monsters_batch_7.json",
        "/home/ubuntu/parsed_monsters_batch_8.json",
        "/home/ubuntu/parsed_monsters_batch_9.json",
        "/home/ubuntu/parsed_monsters_batch_10.json",
        "/home/ubuntu/parsed_monsters_batch_11.json",
        "/home/ubuntu/parsed_monsters_batch_12.json"
    ]
    
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
    
    # Анализируем уже спарсенные данные
    core_sources, monsters = analyze_sources()
    
    print("\n" + "=" * 40)
    
    # Создаем фильтр
    filter_sources = create_core_filter()
    
    # Сохраняем список Core источников
    with open('/home/ubuntu/core_sources.json', 'w', encoding='utf-8') as f:
        json.dump(list(filter_sources), f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Список Core источников сохранен в core_sources.json")

