# Monster Parser Scripts

Набор скриптов для парсинга данных о монстрах D&D 5e с сайта dnd.su и обновления файла `seed_data_monsters.json`.

## Описание скриптов

### Основные парсеры
- `dnd_su_parser_v3.py` - Базовый парсер для извлечения данных о монстрах с dnd.su
- `filtered_mass_parser.py` - Фильтрованный массовый парсер (только Core источники)
- `run_core_parsing.py` - Скрипт запуска парсинга Core монстров

### Анализ и обновление данных
- `check_translation_quality_v2.py` - Анализ качества русских переводов в исходном JSON
- `update_monsters_json.py` - Обновление исходного JSON файла данными из парсера
- `complete_workflow.py` - Полный workflow: парсинг → обновление → git операции

### Вспомогательные скрипты
- `analyze_sources.py` - Анализ источников монстров
- `git_operations.py` - Операции с git репозиторием

## Использование

### Быстрый старт
```bash
# Запуск полного процесса обновления данных
python3 complete_workflow.py
```

### Пошаговое выполнение
```bash
# 1. Парсинг Core монстров
python3 run_core_parsing.py

# 2. Анализ качества переводов
python3 check_translation_quality_v2.py

# 3. Обновление JSON файла
python3 update_monsters_json.py

# 4. Git операции
python3 git_operations.py
```

## Фильтрация источников

Парсер настроен на извлечение только официальных Core источников D&D 5e:
- Basic Rules (без указания источника)
- Monster Manual (MM)
- Player's Handbook (PHB)
- Dungeon Master's Guide (DMG)
- System Reference Document (SRD)
- Mordenkainen Presents: Monsters of the Multiverse (MPMM)

## Требования

- Python 3.7+
- requests
- beautifulsoup4
- git (настроенный с учетными данными)

## Структура данных

Парсер извлекает следующие поля:
- `name` - Русское название
- `english_name` - Английское название
- `description` - Описание на русском
- `source` - Источник (книга)
- `armor_class` - Класс доспеха
- `hit_points` - Хиты
- `challenge_rating` - Рейтинг опасности
- `size` - Размер
- `type` - Тип существа
- И другие доступные характеристики

## Примечания

- Парсер использует задержки между запросами для предотвращения блокировки
- Промежуточные результаты сохраняются каждые 25 монстров
- Все ошибки логируются для последующего анализа
- Поддерживается возобновление парсинга с места остановки

