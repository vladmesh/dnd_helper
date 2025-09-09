# Monster Parser Scripts

Note: this is NOT a microservice. It is a one-off preparatory tool and is not part of the product runtime workflow. Run it via a dedicated Docker image.

## Containerized usage (one-off)

Build the image:
```bash
docker build -f scripts/monster_parser/Dockerfile -t dnd_helper/monster_parser:latest .
```

Run any script inside the container (examples):
```bash
# Example: filtered core parsing (test mode)
docker run --rm -v "$PWD":/app -w /app/scripts/monster_parser dnd_helper/monster_parser:latest \
  python3 filtered_mass_parser.py

# Example: update Russian translations (current version uses absolute paths; will be parameterized next)
docker run --rm -v "$PWD":/app -w /app/scripts/monster_parser dnd_helper/monster_parser:latest \
  python3 update_monster_translations.py
```

Important: some scripts currently contain hardcoded absolute paths (`/home/ubuntu/...`). These will be removed in the next step by adding CLI arguments and repo-relative defaults. The Dockerfile is provided now to enable consistent, isolated execution.

## Defaults and repo paths

- Input seed (default): `/app/seed_data_monsters.json`
- Output seed (default): `/app/seed_data_monsters_updated.json`
- Parser outputs dir (default): `/app/scripts/monster_parser/output`
- Final parsed file (default): `/app/scripts/monster_parser/output/parsed_monsters_filtered_final.json`
- Reports dir (default): `/app/scripts/monster_parser/output/reports`

Run with the repository mounted into the container at `/app`:
```bash
docker build -f scripts/monster_parser/Dockerfile -t dnd_helper/monster_parser:latest .
docker run --rm -v "$PWD":/app -w /app/scripts/monster_parser dnd_helper/monster_parser:latest python3 --version
```

## CLI parameters

### filtered_mass_parser.py
- `--bestiary-url`: root bestiary URL (default: `https://dnd.su/bestiary/`)
- `--allowed-source`: repeatable sources to include (default: `''`, `MM`, `PHB`, `DMG`, `SRD`, `MPMM`)
- `--batch-size`: save batch size (default: `25`)
- `--delay`: delay between requests in seconds (default: `0.5`)
- `--output-dir`: output directory (default: `/app/scripts/monster_parser/output`)
- `--final-file-name`: final JSON filename (default: `parsed_monsters_filtered_final.json`)
- `--test-limit`: limit number of monsters to parse (default: `0` — unlimited)
- `--pagination`: enable pagination (flag; default: off; server-filtered mode always paginates)
- `--allowed-sources-file`: path to a file with allowed sources (one per line). Used when `--allowed-source` flags are not provided. Default: `/app/scripts/monster_parser/allowed_sources.txt`
- `--server-filtered-url`: listing URL with server-side filters (e.g., `https://dnd.su/bestiary/?search=&source=102%7C101%7C103%7C158%7C111%7C109`)

Example:
```bash
docker run --rm -v "$PWD":/app -w /app/scripts/monster_parser dnd_helper/monster_parser:latest \
  python3 filtered_mass_parser.py \
    --server-filtered-url 'https://dnd.su/bestiary/?search=&source=102%7C101%7C103%7C158%7C111%7C109' \
    --output-dir /app/scripts/monster_parser/output \
    --final-file-name parsed_monsters_filtered_final.json \
    --test-limit 20
```

### update_monster_translations.py
- `--seed-in`: path to input seed JSON (default: `/app/seed_data_monsters.json`)
- `--seed-out`: path to output updated seed JSON (default: `/app/seed_data_monsters_updated.json`)
- `--parsed-in`: path to parsed monsters JSON (default: `/app/scripts/monster_parser/output/parsed_monsters_filtered_final.json`)
- `--lang`: target translation language (default: `ru`)
- `--fill-description`: fill empty descriptions (flag; default: on)
- `--replace-english-names`: replace English names with Russian (flag; default: on)
- `--add-english-name`: add `english_name` if missing (flag; default: on)
- `--similarity-threshold`: fuzzy match threshold [0..1] (default: `0.7`)
- `--dry-run`: do not write output, only report (flag; default: off)
- `--limit`: limit number of updates (default: `0` — unlimited)

Matching logic:
- Primary: exact normalized match of RU seed name with parsed RU name or parsed EN name.
- Fallback: if there is no match, try English name from our seed (`monster_translations` with `lang='en'`) by the same `monster_slug` against parsed RU/EN names.

Example:
```bash
docker run --rm -v "$PWD":/app -w /app/scripts/monster_parser dnd_helper/monster_parser:latest \
  python3 update_monster_translations.py \
    --seed-in /app/seed_data_monsters.json \
    --seed-out /app/seed_data_monsters_updated.json \
    --parsed-in /app/scripts/monster_parser/output/parsed_monsters_filtered_final.json \
    --similarity-threshold 0.72
```

### analyze_sources.py
- `--inputs`: glob pattern of parsed batch files (default: `/app/scripts/monster_parser/output/parsed_monsters_filtered_batch_*.json`)
- `--final`: optional path to final parsed file to include
- `--report-out`: path to write sources report JSON (default: `/app/scripts/monster_parser/output/reports/sources.json`)

Example:
```bash
docker run --rm -v "$PWD":/app -w /app/scripts/monster_parser dnd_helper/monster_parser:latest \
  python3 analyze_sources.py \
    --inputs '/app/scripts/monster_parser/output/parsed_monsters_filtered_batch_*.json' \
    --report-out /app/scripts/monster_parser/output/reports/sources.json
```

### check_translation_quality_v2.py
- `--seed-in`: path to seed JSON (default: `/app/seed_data_monsters.json`)
- `--lang`: language (default: `ru`)
- `--report-dir`: directory for reports (default: `/app/scripts/monster_parser/output/reports`)
- `--english-ratio-threshold`: max allowed share of Latin letters (default: `0.3`)

Example:
```bash
docker run --rm -v "$PWD":/app -w /app/scripts/monster_parser dnd_helper/monster_parser:latest \
  python3 check_translation_quality_v2.py \
    --seed-in /app/seed_data_monsters.json \
    --report-dir /app/scripts/monster_parser/output/reports \
    --english-ratio-threshold 0.3
```

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

