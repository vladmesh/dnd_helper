#!/usr/bin/env python3
import os
import time
import json
from update_monsters_json import MonsterDataUpdater
from git_operations import GitOperations

def wait_for_parsing_completion():
    """Ожидает завершения парсинга"""
    print("⏳ Ожидаю завершения парсинга...")
    
    parsed_file = "/home/ubuntu/parsed_monsters_final.json"
    
    while True:
        if os.path.exists(parsed_file):
            try:
                with open(parsed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Проверяем, что файл содержит данные
                if isinstance(data, dict) and 'monsters' in data:
                    monster_count = len(data['monsters'])
                    if monster_count > 100:  # Ожидаем значительное количество монстров
                        print(f"✅ Парсинг завершен! Найдено {monster_count} монстров")
                        return True, parsed_file
                
            except (json.JSONDecodeError, KeyError):
                pass
        
        print("⏳ Парсинг еще не завершен, жду 30 секунд...")
        time.sleep(30)

def analyze_parsing_results(parsed_file):
    """Анализирует результаты парсинга"""
    print("\n📊 Анализ результатов парсинга:")
    
    with open(parsed_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    monsters = data.get('monsters', [])
    errors = data.get('errors', [])
    
    print(f"  Всего монстров: {len(monsters)}")
    print(f"  Ошибок: {len(errors)}")
    print(f"  Процент успеха: {data.get('success_rate', 0):.1f}%")
    
    # Анализируем качество данных
    with_names = sum(1 for m in monsters if m.get('name'))
    with_english_names = sum(1 for m in monsters if m.get('english_name'))
    with_descriptions = sum(1 for m in monsters if m.get('description'))
    
    print(f"  С русскими названиями: {with_names}/{len(monsters)} ({with_names/len(monsters)*100:.1f}%)")
    print(f"  С английскими названиями: {with_english_names}/{len(monsters)} ({with_english_names/len(monsters)*100:.1f}%)")
    print(f"  С описаниями: {with_descriptions}/{len(monsters)} ({with_descriptions/len(monsters)*100:.1f}%)")
    
    return {
        'total_monsters': len(monsters),
        'total_errors': len(errors),
        'success_rate': data.get('success_rate', 0),
        'with_names': with_names,
        'with_english_names': with_english_names,
        'with_descriptions': with_descriptions
    }

def main():
    print("🚀 ЗАПУСК ПОЛНОГО WORKFLOW ОБНОВЛЕНИЯ МОНСТРОВ")
    print("=" * 60)
    
    # Шаг 1: Ожидаем завершения парсинга
    parsing_completed, parsed_file = wait_for_parsing_completion()
    if not parsing_completed:
        print("❌ Парсинг не завершен")
        return
    
    # Шаг 2: Анализируем результаты парсинга
    stats = analyze_parsing_results(parsed_file)
    
    # Шаг 3: Обновляем исходный JSON файл
    print("\n🔄 Обновление исходного JSON файла...")
    
    original_json = "/home/ubuntu/dnd_helper/seed_data_monsters.json"
    output_json = "/home/ubuntu/seed_data_monsters_updated.json"
    
    updater = MonsterDataUpdater(original_json, parsed_file)
    update_success = updater.run_update(output_json)
    
    if not update_success:
        print("❌ Не удалось обновить JSON файл")
        return
    
    # Шаг 4: Создаем статистику для коммита
    stats_message = f"""Статистика обновления:
- Обработано {stats['total_monsters']} монстров из парсера
- Процент успеха парсинга: {stats['success_rate']:.1f}%
- Монстры с русскими названиями: {stats['with_names']}
- Монстры с описаниями: {stats['with_descriptions']}

Источник: автоматический парсинг dnd.su/bestiary/"""
    
    # Шаг 5: Выполняем git операции
    print("\n🌿 Выполнение git операций...")
    
    git_ops = GitOperations()
    git_success, pr_url = git_ops.run_full_workflow(output_json, stats_message)
    
    if git_success:
        print(f"\n🎉 WORKFLOW ЗАВЕРШЕН УСПЕШНО!")
        print(f"✅ JSON файл обновлен и загружен в репозиторий")
        print(f"🔗 Pull Request создан: {pr_url}")
        print(f"📊 Статистика:")
        print(f"   - Обработано {stats['total_monsters']} монстров")
        print(f"   - Процент успеха: {stats['success_rate']:.1f}%")
    else:
        print(f"\n❌ Ошибка в git операциях")
        print(f"📁 Обновленный файл сохранен локально: {output_json}")

if __name__ == "__main__":
    main()

