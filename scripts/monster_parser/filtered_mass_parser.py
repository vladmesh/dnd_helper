#!/usr/bin/env python3
from dnd_su_parser_v3 import DnDSuParserV3
import json
import time
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

class FilteredMassParser(DnDSuParserV3):
    def __init__(self, allowed_sources=None):
        super().__init__()
        self.delay = 0.5  # Задержка между запросами в секундах
        
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
        
        print(f"🎯 Фильтр источников активен. Разрешенные источники: {sorted(self.allowed_sources)}")
    
    def is_allowed_source(self, source):
        """Проверяет, разрешен ли источник"""
        if not source:
            source = ''  # Пустая строка для монстров без источника
        
        return source in self.allowed_sources
    
    def get_filtered_monster_links(self):
        """Получает ссылки только на монстров из разрешенных источников"""
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
            for i, monster_link in enumerate(all_monster_links):
                if (i + 1) % 100 == 0:
                    print(f"Проверено {i + 1}/{len(all_monster_links)} монстров...")
                
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
    
    def run_filtered_parsing(self, test_mode=False):
        """Запускает фильтрованный парсинг"""
        print("🚀 Запуск фильтрованного парсинга (только Core источники)")
        print("=" * 60)
        
        # Получаем отфильтрованный список монстров
        monster_links = self.get_filtered_monster_links()
        
        if not monster_links:
            print("❌ Не удалось получить отфильтрованный список монстров")
            return None, [], []
        
        if test_mode:
            print("🧪 Тестовый режим: парсинг первых 20 монстров")
            monster_links = monster_links[:20]
        
        all_results = []
        all_errors = []
        batch_size = 25
        
        # Парсим по партиям
        for start_idx in range(0, len(monster_links), batch_size):
            batch_num = (start_idx // batch_size) + 1
            
            batch_results, batch_errors = self.parse_monsters_batch(
                monster_links, start_idx, batch_size
            )
            
            all_results.extend(batch_results)
            all_errors.extend(batch_errors)
            
            # Сохраняем промежуточные результаты
            suffix = f"_filtered_batch_{batch_num}"
            self.save_results(all_results, all_errors, suffix)
            
            print(f"\n📈 Прогресс: {len(all_results)} из {len(monster_links)} обработано")
            
            # Небольшая пауза между партиями
            if start_idx + batch_size < len(monster_links):
                time.sleep(2)
        
        # Финальное сохранение
        final_file = self.save_results(all_results, all_errors, "_filtered_final")
        
        print(f"\n🎉 Фильтрованный парсинг завершен!")
        print(f"✅ Успешно обработано: {len(all_results)} Core монстров")
        print(f"❌ Ошибок: {len(all_errors)}")
        print(f"📈 Процент успеха: {(len(all_results) / len(monster_links)) * 100:.1f}%")
        
        # Анализ качества данных
        self.analyze_data_quality(all_results)
        
        return final_file, all_results, all_errors
    
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
        
        filename = f'/home/ubuntu/parsed_monsters{suffix}.json'
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
    # Настройка источников
    core_sources = ['', 'MM', 'PHB', 'DMG', 'SRD']  # Без MPMM пока
    
    parser = FilteredMassParser(allowed_sources=core_sources)
    
    # Запускаем в тестовом режиме
    final_file, results, errors = parser.run_filtered_parsing(test_mode=True)
    
    if results:
        print(f"\n✨ Фильтрованный парсинг завершен!")
        print(f"📁 Результаты сохранены в: {final_file}")
    else:
        print(f"\n😞 Фильтрованный парсинг не дал результатов")

if __name__ == "__main__":
    main()

