#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin, urlparse

class DnDSuParserV3:
    def __init__(self):
        self.base_url = "https://dnd.su"
        self.bestiary_url = "https://dnd.su/bestiary/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def parse_monster_page(self, url):
        """Улучшенный парсер с корректным извлечением английских названий"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            monster_data = {
                'url': url,
                'name': '',
                'english_name': '',
                'source': '',
                'size_and_type': '',
                'armor_class': '',
                'hit_points': '',
                'speed': '',
                'abilities': {},
                'saving_throws': '',
                'skills': '',
                'senses': '',
                'languages': '',
                'challenge_rating': '',
                'proficiency_bonus': '',
                'traits': [],
                'actions': [],
                'bonus_actions': [],
                'legendary_actions': [],
                'description': ''
            }
            
            # Получаем весь текст страницы для анализа
            page_text = soup.get_text()
            
            # 1. Извлекаем название и английское название из заголовка h2
            h2_tags = soup.find_all('h2')
            for h2 in h2_tags:
                h2_text = h2.get_text(strip=True)
                
                # Ищем заголовок с английским названием в формате "Русское [English]ИСТОЧНИК"
                bracket_match = re.search(r'^([^[]+)\s*\[([^\]]+)\]\s*([A-Z]+)?\s*$', h2_text)
                if bracket_match:
                    monster_data['name'] = bracket_match.group(1).strip()
                    monster_data['english_name'] = bracket_match.group(2).strip()
                    if bracket_match.group(3):
                        monster_data['source'] = bracket_match.group(3).strip()
                    break
            
            # Если не найдено в h2, пробуем другие методы
            if not monster_data['name']:
                # Метод 2: Из title страницы
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text()
                    if ' / ' in title_text:
                        main_part = title_text.split(' / ')[0].strip()
                        monster_data['name'] = main_part
            
            # Если не найден источник, ищем его отдельно
            if not monster_data['source']:
                source_match = re.search(r'\]\s*([A-Z]{2,5})\s', page_text)
                if source_match:
                    monster_data['source'] = source_match.group(1)
            
            # 2. Извлекаем размер и тип
            size_type_patterns = [
                r'(Крошечная|Маленькая|Средняя|Большая|Огромная|Гигантская)\s+([^,]+),\s*([^,\n]+)',
                r'(Крошечная|Маленькая|Средняя|Большая|Огромная|Гигантская)\s*\?\s+([^,]+),\s*([^,\n]+)'
            ]
            
            for pattern in size_type_patterns:
                size_type_match = re.search(pattern, page_text)
                if size_type_match:
                    size = size_type_match.group(1)
                    creature_type = size_type_match.group(2).strip()
                    alignment = size_type_match.group(3).strip()
                    monster_data['size_and_type'] = f"{size} {creature_type}, {alignment}"
                    break
            
            # 3. Класс доспеха
            ac_match = re.search(r'Класс Доспеха\s+(\d+)(?:\s*\(([^)]+)\))?', page_text)
            if ac_match:
                ac_value = ac_match.group(1)
                ac_type = ac_match.group(2) if ac_match.group(2) else ""
                monster_data['armor_class'] = f"{ac_value} ({ac_type})" if ac_type else ac_value
            
            # 4. Хиты
            hp_match = re.search(r'Хиты\s+(\d+)(?:\s*\(([^)]+)\))?', page_text)
            if hp_match:
                hp_value = hp_match.group(1)
                hp_dice = hp_match.group(2) if hp_match.group(2) else ""
                monster_data['hit_points'] = f"{hp_value} ({hp_dice})" if hp_dice else hp_value
            
            # 5. Скорость
            speed_match = re.search(r'Скорость\s+([^\n]+)', page_text)
            if speed_match:
                monster_data['speed'] = speed_match.group(1).strip()
            
            # 6. Характеристики (улучшенный поиск с учетом разных форматов)
            ability_patterns = [
                r'Сил\s+Лов\s+Тел\s+Инт\s+Мдр\s+Хар\s+(\d+)\s*\([+-]?\d+\)\s+(\d+)\s*\([+-]?\d+\)\s+(\d+)\s*\([+-]?\d+\)\s+(\d+)\s*\([+-]?\d+\)\s+(\d+)\s*\([+-]?\d+\)\s+(\d+)\s*\([+-]?\d+\)',
                r'(\d+)\s*\([+-]?\d+\)\s+(\d+)\s*\([+-]?\d+\)\s+(\d+)\s*\([+-]?\d+\)\s+(\d+)\s*\([+-]?\d+\)\s+(\d+)\s*\([+-]?\d+\)\s+(\d+)\s*\([+-]?\d+\)'
            ]
            
            for pattern in ability_patterns:
                ability_match = re.search(pattern, page_text)
                if ability_match:
                    monster_data['abilities'] = {
                        'str': int(ability_match.group(1)),
                        'dex': int(ability_match.group(2)),
                        'con': int(ability_match.group(3)),
                        'int': int(ability_match.group(4)),
                        'wis': int(ability_match.group(5)),
                        'cha': int(ability_match.group(6))
                    }
                    break
            
            # 7. Остальные поля (без изменений)
            saves_match = re.search(r'Спасброски\s+([^\n]+)', page_text)
            if saves_match:
                monster_data['saving_throws'] = saves_match.group(1).strip()
            
            skills_match = re.search(r'Навыки\s+([^\n]+)', page_text)
            if skills_match:
                monster_data['skills'] = skills_match.group(1).strip()
            
            senses_match = re.search(r'Чувства\s+([^\n]+)', page_text)
            if senses_match:
                monster_data['senses'] = senses_match.group(1).strip()
            
            languages_match = re.search(r'Языки\s+([^\n]+)', page_text)
            if languages_match:
                monster_data['languages'] = languages_match.group(1).strip()
            
            cr_match = re.search(r'Опасность\s+([^\s]+)(?:\s*\(([^)]+)\s+опыта\))?', page_text)
            if cr_match:
                cr_value = cr_match.group(1)
                xp_value = cr_match.group(2) if cr_match.group(2) else ""
                monster_data['challenge_rating'] = f"{cr_value} ({xp_value} опыта)" if xp_value else cr_value
            
            prof_match = re.search(r'Бонус мастерства\s*([+-]?\d+)', page_text)
            if prof_match:
                monster_data['proficiency_bonus'] = prof_match.group(1)
            
            # 8. Описание
            description_text = ""
            desc_header = soup.find(['h3', 'h4'], string=re.compile(r'Описание', re.IGNORECASE))
            if desc_header:
                current = desc_header.next_sibling
                while current:
                    if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        break
                    if hasattr(current, 'get_text'):
                        text = current.get_text(strip=True)
                        if text:
                            description_text += text + " "
                    elif isinstance(current, str):
                        text = current.strip()
                        if text:
                            description_text += text + " "
                    current = current.next_sibling
            
            if not description_text.strip():
                paragraphs = soup.find_all('p')
                for p in reversed(paragraphs):
                    text = p.get_text(strip=True)
                    if len(text) > 100:
                        description_text = text
                        break
            
            monster_data['description'] = description_text.strip()
            
            return monster_data
            
        except Exception as e:
            print(f"Ошибка при парсинге {url}: {e}")
            return None
    
    def test_single_monster(self, url):
        """Тестирует улучшенный парсинг одного монстра"""
        print(f"Тестирую исправленный парсинг: {url}")
        monster_data = self.parse_monster_page(url)
        
        if monster_data:
            print("Успешно извлечены данные:")
            print(f"  Название: '{monster_data['name']}'")
            print(f"  Английское название: '{monster_data['english_name']}'")
            print(f"  Источник: '{monster_data['source']}'")
            print(f"  Размер и тип: '{monster_data['size_and_type']}'")
            print(f"  Класс доспеха: '{monster_data['armor_class']}'")
            print(f"  Хиты: '{monster_data['hit_points']}'")
            print(f"  Скорость: '{monster_data['speed']}'")
            print(f"  Опасность: '{monster_data['challenge_rating']}'")
            print(f"  Характеристики: {monster_data['abilities']}")
            print(f"  Описание: {len(monster_data['description'])} символов")
            
            return monster_data
        else:
            print("Не удалось извлечь данные")
            return None

if __name__ == "__main__":
    parser = DnDSuParserV3()
    
    # Тестируем на том же монстре
    test_url = "https://dnd.su/bestiary/7813-alyxian-aboleth/"
    result = parser.test_single_monster(test_url)
    
    if result:
        # Сохраняем результат исправленного тестирования
        with open('/home/ubuntu/test_monster_data_v3.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("Исправленные данные сохранены в test_monster_data_v3.json")

