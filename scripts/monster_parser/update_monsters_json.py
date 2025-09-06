#!/usr/bin/env python3
import json
import re
from difflib import SequenceMatcher

class MonsterDataUpdater:
    def __init__(self, original_json_path, parsed_data_path):
        self.original_json_path = original_json_path
        self.parsed_data_path = parsed_data_path
        self.original_monsters = []
        self.parsed_monsters = []
        
    def load_data(self):
        """Загружает исходные и спарсенные данные"""
        print("Загружаю исходный JSON файл...")
        with open(self.original_json_path, 'r', encoding='utf-8') as f:
            self.original_monsters = json.load(f)
        print(f"Загружено {len(self.original_monsters)} монстров из исходного файла")
        
        print("Загружаю результаты парсинга...")
        with open(self.parsed_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and 'monsters' in data:
                self.parsed_monsters = data['monsters']
            else:
                self.parsed_monsters = data
        print(f"Загружено {len(self.parsed_monsters)} монстров из результатов парсинга")
    
    def normalize_name(self, name):
        """Нормализует название для сравнения"""
        if not name:
            return ""
        
        # Убираем лишние символы и приводим к нижнему регистру
        normalized = re.sub(r'[^\w\s]', '', str(name).lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Убираем общие суффиксы/префиксы
        normalized = re.sub(r'\s*(именной\s*нип|и)$', '', normalized)
        
        return normalized
    
    def similarity(self, a, b):
        """Вычисляет схожесть двух строк"""
        return SequenceMatcher(None, a, b).ratio()
    
    def find_matching_monster(self, original_monster):
        """Находит соответствующего монстра в результатах парсинга"""
        best_match = None
        best_score = 0
        
        # Получаем возможные названия для поиска из исходного монстра
        search_names = []
        
        # Русское название
        if original_monster.get('name'):
            search_names.append(self.normalize_name(original_monster['name']))
        
        # Английское название
        if original_monster.get('english_name'):
            search_names.append(self.normalize_name(original_monster['english_name']))
        
        # Slug из URL (если есть)
        if original_monster.get('slug'):
            search_names.append(self.normalize_name(original_monster['slug']))
        
        # Ищем среди спарсенных монстров
        for parsed_monster in self.parsed_monsters:
            parsed_names = []
            
            # Русское название
            if parsed_monster.get('name'):
                parsed_names.append(self.normalize_name(parsed_monster['name']))
            
            # Английское название
            if parsed_monster.get('english_name'):
                parsed_names.append(self.normalize_name(parsed_monster['english_name']))
            
            # Сравниваем все комбинации
            for search_name in search_names:
                for parsed_name in parsed_names:
                    if search_name and parsed_name:
                        score = self.similarity(search_name, parsed_name)
                        if score > best_score and score > 0.7:  # Порог схожести 70%
                            best_score = score
                            best_match = parsed_monster
        
        return best_match, best_score
    
    def is_english_text(self, text):
        """Проверяет, является ли текст английским"""
        if not text:
            return False
        
        # Подсчитываем латинские и кириллические символы
        latin_chars = len(re.findall(r'[a-zA-Z]', text))
        cyrillic_chars = len(re.findall(r'[а-яА-ЯёЁ]', text))
        
        # Если латинских символов больше, считаем текст английским
        return latin_chars > cyrillic_chars
    
    def needs_update(self, original_monster):
        """Определяет, нужно ли обновлять монстра"""
        # Проверяем название
        name = original_monster.get('name', '')
        if not name or self.is_english_text(name):
            return True, 'name'
        
        # Проверяем описание
        description = original_monster.get('description', '')
        if not description or self.is_english_text(description):
            return True, 'description'
        
        return False, None
    
    def update_monster_data(self, original_monster, parsed_monster):
        """Обновляет данные монстра"""
        updated = False
        
        # Обновляем название, если нужно
        if not original_monster.get('name') or self.is_english_text(original_monster.get('name', '')):
            if parsed_monster.get('name'):
                original_monster['name'] = parsed_monster['name']
                updated = True
                print(f"  Обновлено название: {parsed_monster['name']}")
        
        # Обновляем описание, если нужно
        if not original_monster.get('description') or self.is_english_text(original_monster.get('description', '')):
            if parsed_monster.get('description'):
                original_monster['description'] = parsed_monster['description']
                updated = True
                print(f"  Обновлено описание: {len(parsed_monster['description'])} символов")
        
        # Дополнительно обновляем английское название, если его нет
        if not original_monster.get('english_name') and parsed_monster.get('english_name'):
            original_monster['english_name'] = parsed_monster['english_name']
            updated = True
            print(f"  Добавлено английское название: {parsed_monster['english_name']}")
        
        return updated
    
    def process_updates(self):
        """Обрабатывает обновления всех монстров"""
        print("\nНачинаю обработку обновлений...")
        
        total_updated = 0
        total_needs_update = 0
        not_found = 0
        
        for i, original_monster in enumerate(self.original_monsters):
            if (i + 1) % 100 == 0:
                print(f"Обработано {i + 1}/{len(self.original_monsters)} монстров...")
            
            needs_update, field = self.needs_update(original_monster)
            if not needs_update:
                continue
            
            total_needs_update += 1
            
            # Ищем соответствующего монстра в результатах парсинга
            matched_monster, score = self.find_matching_monster(original_monster)
            
            if matched_monster:
                print(f"\n[{i+1}] Найдено соответствие (схожесть: {score:.2f}):")
                print(f"  Исходный: {original_monster.get('name', 'Без названия')}")
                print(f"  Найденный: {matched_monster.get('name', 'Без названия')}")
                
                if self.update_monster_data(original_monster, matched_monster):
                    total_updated += 1
            else:
                not_found += 1
                print(f"\n[{i+1}] Не найдено соответствие для: {original_monster.get('name', 'Без названия')}")
        
        print(f"\n📊 Статистика обновлений:")
        print(f"  Всего монстров: {len(self.original_monsters)}")
        print(f"  Нуждались в обновлении: {total_needs_update}")
        print(f"  Успешно обновлено: {total_updated}")
        print(f"  Не найдено соответствий: {not_found}")
        print(f"  Процент успеха: {(total_updated/total_needs_update*100):.1f}%" if total_needs_update > 0 else "N/A")
        
        return total_updated
    
    def save_updated_data(self, output_path):
        """Сохраняет обновленные данные"""
        print(f"\nСохраняю обновленные данные в {output_path}...")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.original_monsters, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Обновленные данные сохранены!")
    
    def run_update(self, output_path):
        """Запускает полный процесс обновления"""
        print("🚀 Запуск обновления данных о монстрах")
        print("=" * 50)
        
        self.load_data()
        total_updated = self.process_updates()
        
        if total_updated > 0:
            self.save_updated_data(output_path)
            return True
        else:
            print("Нет данных для обновления")
            return False

def main():
    # Пути к файлам
    original_json = "/home/ubuntu/dnd_helper/seed_data_monsters.json"
    parsed_data = "/home/ubuntu/parsed_monsters_final.json"  # Будет обновлен после завершения парсинга
    output_json = "/home/ubuntu/seed_data_monsters_updated.json"
    
    updater = MonsterDataUpdater(original_json, parsed_data)
    success = updater.run_update(output_json)
    
    if success:
        print(f"\n🎉 Обновление завершено успешно!")
        print(f"📁 Обновленный файл: {output_json}")
    else:
        print(f"\n😞 Обновление не выполнено")

if __name__ == "__main__":
    main()

