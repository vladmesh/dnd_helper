#!/usr/bin/env python3
from filtered_mass_parser import FilteredMassParser

def main():
    print("🚀 ЗАПУСК CORE ПАРСИНГА (только официальные источники)")
    print("=" * 60)
    
    # Настройка Core источников (включая MPMM)
    core_sources = [
        '',      # Basic Rules (без указания источника)
        'MM',    # Monster Manual
        'PHB',   # Player's Handbook
        'DMG',   # Dungeon Master's Guide
        'SRD',   # System Reference Document
        'MPMM'   # Mordenkainen Presents: Monsters of the Multiverse
    ]
    
    print("🎯 Core источники:")
    for source in core_sources:
        source_name = {
            '': 'Basic Rules (без источника)',
            'MM': 'Monster Manual',
            'PHB': "Player's Handbook",
            'DMG': "Dungeon Master's Guide", 
            'SRD': 'System Reference Document',
            'MPMM': 'Mordenkainen Presents: Monsters of the Multiverse'
        }.get(source, source)
        print(f"  - {source or 'Пустая строка'}: {source_name}")
    
    print("\n" + "=" * 60)
    
    # Создаем парсер с фильтром
    parser = FilteredMassParser(allowed_sources=core_sources)
    
    # Запускаем сначала в тестовом режиме
    print("🧪 Тестовый режим: проверяем первые 20 Core монстров")
    final_file, results, errors = parser.run_filtered_parsing(test_mode=True)
    
    if results:
        print(f"\n✅ Тестовый парсинг успешен!")
        print(f"📊 Найдено {len(results)} Core монстров")
        print(f"📁 Результаты: {final_file}")
        
        # Спрашиваем, продолжать ли полный парсинг
        print(f"\n🤔 Продолжить полный парсинг всех Core монстров? (y/n)")
        # В автоматическом режиме продолжаем
        continue_full = True
        
        if continue_full:
            print(f"\n🚀 Запуск полного Core парсинга...")
            final_file_full, results_full, errors_full = parser.run_filtered_parsing(test_mode=False)
            
            if results_full:
                print(f"\n🎉 ПОЛНЫЙ CORE ПАРСИНГ ЗАВЕРШЕН!")
                print(f"✅ Обработано {len(results_full)} Core монстров")
                print(f"❌ Ошибок: {len(errors_full)}")
                print(f"📁 Финальный файл: {final_file_full}")
                
                return final_file_full, results_full, errors_full
            else:
                print(f"\n😞 Полный парсинг не дал результатов")
                return None, [], []
        else:
            return final_file, results, errors
    else:
        print(f"\n😞 Тестовый парсинг не дал результатов")
        return None, [], []

if __name__ == "__main__":
    main()

