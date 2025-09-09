#!/usr/bin/env python3
from dnd_su_parser_v3 import DnDSuParserV3
import json
import time
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import argparse
import os
import sys

class FilteredMassParser(DnDSuParserV3):
    def __init__(self, allowed_sources=None, output_dir="/app/scripts/monster_parser/output", final_file_name="parsed_monsters_filtered_final.json", delay=0.5):
        super().__init__()
        self.delay = delay
        self.output_dir = output_dir
        self.final_file_name = final_file_name

        # Список разрешенных источников
        if allowed_sources is None:
            # По умолчанию - только Core источники
            self.allowed_sources = {
                '',      # Без указания источника (Basic Rules)
                'MM',    # Monster Manual
                'PHB',   # Player's Handbook
                'DMG',   # Dungeon Master's Guide
                'SRD',   # System Reference Document
                'MPMM'   # Mordenkainen Presents: Monsters of the Multiverse (обновленный MM)
            }
        else:
            self.allowed_sources = set(allowed_sources)

        os.makedirs(self.output_dir, exist_ok=True)
    
    def is_allowed_source(self, source):
        """Проверяет, разрешен ли источник"""
        if not source:
            source = ''  # Пустая строка для монстров без источника
        
        return source in self.allowed_sources
    
    def get_filtered_monster_links(self, limit: int | None = None):
        """Получает ссылки только на монстров из разрешенных источников.
        Если передан limit > 0, прекращает после набора нужного количества отфильтрованных ссылок.
        """
        print("Получаю список монстров с фильтрацией по источникам...")
        
        try:
            response = self.session.get(self.bestiary_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем все ссылки на монстров
            all_monster_links = []
            filtered_monster_links = []
            
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                text = link.get_text(strip=True)
                
                # Проверяем, что это ссылка на монстра
                if (href and '/bestiary/' in href and 
                    text and re.match(r'^\[.*\]', text)):
                    
                    full_url = urljoin(self.base_url, href)
                    
                    # Избегаем дубликатов
                    if not any(m['url'] == full_url for m in all_monster_links):
                        all_monster_links.append({
                            'name': text,
                            'url': full_url
                        })
            
            print(f"Найдено {len(all_monster_links)} уникальных монстров")
            print("Применяю фильтр по источникам...")
            
            # Фильтруем по источникам
            total_links = len(all_monster_links)
            for i, monster_link in enumerate(all_monster_links):
                # Прогресс сканирования ссылок
                self._print_progress("🔎 Фильтрация", i + 1, total_links)
                
                # Быстро проверяем источник монстра
                try:
                    response = self.session.get(monster_link['url'])
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Извлекаем источник
                    source = ''
                    h2_tags = soup.find_all('h2')
                    for h2 in h2_tags:
                        h2_text = h2.get_text(strip=True)
                        bracket_match = re.search(r'\]\s*([A-Z]{2,5})\s*$', h2_text)
                        if bracket_match:
                            source = bracket_match.group(1)
                            break
                    
                    # Проверяем, разрешен ли источник
                    if self.is_allowed_source(source):
                        filtered_monster_links.append({
                            'name': monster_link['name'],
                            'url': monster_link['url'],
                            'source': source
                        })
                        print(f"✅ {monster_link['name']} (источник: {source or 'Нет'})")
                        # Раннее завершение при тестовом лимите
                        if limit and limit > 0 and len(filtered_monster_links) >= limit:
                            break
                    else:
                        print(f"❌ {monster_link['name']} (источник: {source}) - отфильтрован")
                    
                    # Небольшая задержка
                    time.sleep(0.2)
                    
                except Exception as e:
                    print(f"⚠️ Ошибка проверки {monster_link['name']}: {e}")
                    continue
            
            print(f"\n📊 Результат фильтрации:")
            print(f"  Всего монстров: {len(all_monster_links)}")
            print(f"  Прошли фильтр: {len(filtered_monster_links)}")
            print(f"  Отфильтровано: {len(all_monster_links) - len(filtered_monster_links)}")
            print(f"  Процент Core: {(len(filtered_monster_links)/len(all_monster_links)*100):.1f}%")
            
            return filtered_monster_links

        except Exception as e:
            print(f"Ошибка при получении списка монстров: {e}")
            return []

    def get_monster_links_server_filtered(self, list_url: str, limit: int | None = None):
        """Получает ссылки на монстров со страницы с уже отфильтрованным набором (серверная фильтрация).
        Обходит пагинацию по кнопке/ссылке ">".
        """
        print("Получаю список монстров (server-filtered)...")
        results = []
        page_url = list_url
        visited = set()

        try:
            while page_url and page_url not in visited:
                visited.add(page_url)
                response = self.session.get(page_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                # Ссылки на монстров: ориентируемся на href, текст ссылки может не начинаться с '['
                page_links = []
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if not href:
                        continue
                    if '/bestiary/' not in href:
                        continue
                    # Отсечь сам корень бестиария и якоря/пагинацию
                    if href.rstrip('/') == '/bestiary' or href.rstrip('/') == '/bestiary/':
                        continue
                    full_url = urljoin(self.base_url, href)
                    if not any(m['url'] == full_url for m in results):
                        page_links.append({ 'name': link.get_text(strip=True), 'url': full_url })

                results.extend(page_links)
                print(f"Найдено на странице: {len(page_links)}, всего: {len(results)}")
                if limit and limit > 0 and len(results) >= limit:
                    results = results[:limit]
                    break

                # Пагинация: ищем ссылку на следующую страницу по символу '>'
                next_link = None
                for a in soup.find_all('a', href=True):
                    if a.get_text(strip=True) in ('>', '›', '»'):
                        next_link = urljoin(self.base_url, a['href'])
                        break
                page_url = next_link

            print(f"Итого ссылок: {len(results)}")
            return results
        except Exception as e:
            print(f"Ошибка при получении списка (server-filtered): {e}")
            return results
    
    def parse_monsters_batch(self, monster_links, start_index=0, batch_size=25):
        """Парсит партию отфильтрованных монстров"""
        end_index = min(start_index + batch_size, len(monster_links))
        batch = monster_links[start_index:end_index]
        
        print(f"\nПарсинг партии {start_index+1}-{end_index} из {len(monster_links)} отфильтрованных монстров...")
        
        results = []
        errors = []
        
        for i, monster_link in enumerate(batch):
            global_index = start_index + i + 1
            source_info = f" ({monster_link.get('source', 'Нет источника')})"
            print(f"[{global_index}/{len(monster_links)}] {monster_link['name']}{source_info}")
            
            try:
                monster_data = self.parse_monster_page(monster_link['url'])
                
                if monster_data and monster_data.get('name'):
                    results.append(monster_data)
                    print(f"✅ {monster_data['name']} ({monster_data.get('english_name', 'без англ. названия')})")
                else:
                    errors.append({
                        'url': monster_link['url'],
                        'name': monster_link['name'],
                        'error': 'Пустые данные'
                    })
                    print(f"❌ Пустые данные")
                
            except Exception as e:
                errors.append({
                    'url': monster_link['url'],
                    'name': monster_link['name'],
                    'error': str(e)
                })
                print(f"❌ Ошибка: {e}")
            
            # Задержка между запросами
            if i < len(batch) - 1:
                time.sleep(self.delay)
        
        return results, errors
    
    def run_filtered_parsing(self, test_mode=False, test_limit=0, batch_size=25, server_filtered_url: str | None = None):
        """Запускает парсинг"""
        if server_filtered_url:
            print("🚀 Запуск парсинга (server-filtered)")
        else:
            print("🚀 Запуск парсинга (client-filtered по источникам)")
        print("=" * 60)
        
        # Получаем список монстров
        if server_filtered_url:
            # Серверная фильтрация: берём только то, что вернул сайт (с пагинацией)
            limit = (test_limit if (test_mode and test_limit and test_limit > 0) else None)
            monster_links = self.get_monster_links_server_filtered(server_filtered_url, limit=limit)
        else:
            # Клиентская фильтрация по источникам (старый режим)
            if test_mode and test_limit and test_limit > 0:
                monster_links = self.get_filtered_monster_links(limit=test_limit)
            else:
                monster_links = self.get_filtered_monster_links()
        
        if not monster_links:
            print("❌ Не удалось получить отфильтрованный список монстров")
            return None, [], []
        
        if test_mode:
            limit = test_limit if test_limit and test_limit > 0 else 20
            print(f"🧪 Тестовый режим: парсинг первых {limit} монстров")
            monster_links = monster_links[:limit]
        
        all_results = []
        all_errors = []
        
        # Парсим по партиям
        total = len(monster_links)
        for start_idx in range(0, total, batch_size):
            batch_num = (start_idx // batch_size) + 1
            
            batch_results, batch_errors = self.parse_monsters_batch(
                monster_links, start_idx, batch_size
            )
            
            all_results.extend(batch_results)
            all_errors.extend(batch_errors)
            
            # Сохраняем промежуточные результаты
            suffix = f"_filtered_batch_{batch_num}"
            self.save_results(all_results, all_errors, suffix)
            
            print()
            self._print_progress("📈 Прогресс", len(all_results), total)
            
            # Небольшая пауза между партиями
            if start_idx + batch_size < total:
                time.sleep(2)
        
        # Финальное сохранение
        final_file = os.path.join(self.output_dir, self.final_file_name)
        full_data = {
            'monsters': all_results,
            'errors': all_errors,
            'total_parsed': len(all_results),
            'total_errors': len(all_errors),
            'success_rate': (len(all_results) / (len(all_results) + len(all_errors))) * 100 if (len(all_results) + len(all_errors)) > 0 else 0,
            'allowed_sources': list(self.allowed_sources)
        }
        with open(final_file, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n🎉 Фильтрованный парсинг завершен!")
        print(f"✅ Успешно обработано: {len(all_results)} Core монстров")
        print(f"❌ Ошибок: {len(all_errors)}")
        print(f"📈 Процент успеха: {(len(all_results) / len(monster_links)) * 100:.1f}%")
        
        # Анализ качества данных
        self.analyze_data_quality(all_results)
        
        return final_file, all_results, all_errors
    
    @staticmethod
    def _print_progress(prefix: str, current: int, total: int, bar_len: int = 30):
        if total <= 0:
            return
        ratio = max(0.0, min(1.0, current / total))
        filled = int(bar_len * ratio)
        bar = '█' * filled + '-' * (bar_len - filled)
        percent = int(ratio * 100)
        sys.stdout.write(f"\r{prefix} [{bar}] {current}/{total} ({percent}%)")
        sys.stdout.flush()
        if current >= total:
            print()

    def save_results(self, all_results, all_errors, suffix):
        """Сохраняет результаты с указанным суффиксом"""
        full_data = {
            'monsters': all_results,
            'errors': all_errors,
            'total_parsed': len(all_results),
            'total_errors': len(all_errors),
            'success_rate': (len(all_results) / (len(all_results) + len(all_errors))) * 100 if (len(all_results) + len(all_errors)) > 0 else 0,
            'allowed_sources': list(self.allowed_sources)
        }

        filename = os.path.join(self.output_dir, f'parsed_monsters{suffix}.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2)

        print(f"💾 Результаты сохранены: {filename}")
        return filename
    
    def analyze_data_quality(self, results):
        """Анализирует качество извлеченных данных"""
        if not results:
            return
        
        print(f"\n📊 Анализ качества данных ({len(results)} Core монстров):")
        
        # Подсчитываем заполненность ключевых полей
        key_fields = {
            'name': 'Название',
            'english_name': 'Английское название', 
            'description': 'Описание',
            'source': 'Источник',
            'armor_class': 'Класс доспеха',
            'hit_points': 'Хиты',
            'challenge_rating': 'Опасность'
        }
        
        for field, field_name in key_fields.items():
            filled = sum(1 for m in results if m.get(field) and str(m[field]).strip())
            percentage = (filled / len(results)) * 100
            print(f"  {field_name}: {filled}/{len(results)} ({percentage:.1f}%)")
        
        # Анализ по источникам
        sources = {}
        for monster in results:
            source = monster.get('source', 'Без источника')
            sources[source] = sources.get(source, 0) + 1
        
        print(f"\n📚 Распределение по источникам:")
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            print(f"  {source or 'Без источника'}: {count} монстров")

def main():
    argp = argparse.ArgumentParser(description="Filtered mass parser for dnd.su bestiary (Core sources)")
    argp.add_argument('--bestiary-url', default='https://dnd.su/bestiary/', help='Root bestiary URL')
    argp.add_argument('--allowed-source', action='append', dest='allowed_sources', help='Allowed source code (repeatable). If omitted, defaults file will be used.')
    argp.add_argument('--allowed-sources-file', default='/app/scripts/monster_parser/allowed_sources.txt', help='Path to file with allowed sources (one per line)')
    argp.add_argument('--batch-size', type=int, default=25, help='Batch size for saving intermediate results')
    argp.add_argument('--delay', type=float, default=0.5, help='Delay between HTTP requests in seconds')
    argp.add_argument('--output-dir', default='/app/scripts/monster_parser/output', help='Directory to store outputs')
    argp.add_argument('--final-file-name', default='parsed_monsters_filtered_final.json', help='Final aggregated file name')
    argp.add_argument('--test-limit', type=int, default=0, help='Limit number of monsters in test mode (0 = unlimited)')
    argp.add_argument('--pagination', action='store_true', help='Enable pagination (not used in server-filtered mode, always on there)')
    argp.add_argument('--server-filtered-url', default='', help='Listing URL with server-side filters applied (e.g., dnd.su search with source=...)')
    args = argp.parse_args()

    # Defaults for allowed sources if none provided
    if args.allowed_sources:
        allowed = args.allowed_sources
    else:
        allowed = []
        try:
            with open(args.allowed_sources_file, 'r', encoding='utf-8') as f:
                for line in f:
                    code = line.strip()
                    if code and not code.startswith('#'):
                        allowed.append(code)
        except FileNotFoundError:
            allowed = ['', 'MM', 'PHB', 'DMG', 'SRD', 'MPMM']

    parser = FilteredMassParser(allowed_sources=allowed, output_dir=args.output_dir, final_file_name=args.final_file_name, delay=args.delay)
    # Override bestiary URL if provided
    parser.bestiary_url = args.bestiary_url

    final_file, results, errors = parser.run_filtered_parsing(
        test_mode=True if args.test_limit and args.test_limit > 0 else False,
        test_limit=args.test_limit,
        batch_size=args.batch_size,
        server_filtered_url=args.server_filtered_url or None,
    )

    if results:
        print(f"\n✨ Фильтрованный парсинг завершен!")
        print(f"📁 Результаты сохранены в: {final_file}")
    else:
        print(f"\n😞 Фильтрованный парсинг не дал результатов")

if __name__ == "__main__":
    main()

