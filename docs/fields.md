# D\&D 5e Справочник — Поля и Фильтрация

## Монстры

**Базовые поля:**

* Название
* Тип (гуманоид, нежить, зверь и т. д.)
* Размер (Tiny, Small, Medium, Large, Huge, Gargantuan)
* Мировоззрение
* Класс доспеха (AC)
* Очки здоровья (HP)
* Скорости (ходьба, полёт, плавание, рытьё, лазание)
* Уровень опасности (CR)

**Характеристики:**

* Strength
* Dexterity
* Constitution
* Intelligence
* Wisdom
* Charisma

**Бонусы и спасброски:**

* Saving Throws
* Skills

**Особенности восприятия:**

* Passive Perception
* Darkvision/Blindsight/Tremorsense/Truesight

**Языки**

**Особенности и черты:**

* Traits (например: Pack Tactics, Magic Resistance)
* Legendary Actions
* Actions / Reactions
* Spellcasting (если применимо)

**JSON пример:**

```json
{
  "name": "Goblin",
  "type": "Humanoid",
  "size": "Small",
  "alignment": "Neutral Evil",
  "armor_class": 15,
  "hit_points": 7,
  "speed": {"walk": 30},
  "challenge_rating": 0.25,
  "stats": {"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8},
  "saving_throws": {"dex": "+2"},
  "skills": {"stealth": "+6"},
  "senses": {"darkvision": 60, "passive_perception": 9},
  "languages": ["Common", "Goblin"],
  "traits": ["Nimble Escape"],
  "actions": ["Scimitar", "Shortbow"]
}
```

---

## Заклинания

**Базовые поля:**

* Название
* Школа
* Уровень заклинания
* Компоненты (Verbal, Somatic, Material)
* Длительность
* Дистанция
* Время накладывания
* Концентрация (да/нет)
* Классы, которым доступно

**Эффект:**

* Описание
* Урон (если есть)
* Спасбросок (Dex, Wis и т. д.)
* Тип урона
* Область действия (точка, конус, линия, радиус)

**JSON пример:**

```json
{
  "name": "Fireball",
  "level": 3,
  "school": "Evocation",
  "casting_time": "1 action",
  "range": "150 feet",
  "components": ["V", "S", "M"],
  "duration": "Instantaneous",
  "concentration": false,
  "classes": ["Wizard", "Sorcerer"],
  "effect": {
    "damage": {"type": "fire", "amount": "8d6"},
    "save": "Dexterity",
    "area": {"shape": "sphere", "radius": 20},
    "description": "A bright streak flashes... each creature in a 20-foot-radius sphere must make a Dex saving throw."
  }
}
```

---

## Возможности расширения

**Фильтры и поиск:**

* По CR, типу монстра, размеру
* По урону или типу заклинания
* По условиям (например: паралич, оглушение)
* По доступности классу/способности

**Юзкейсы:**

* Быстрый подбор монстров для боя по уровню группы
* Подбор заклинаний по ситуации (массовый контроль, лечение, урон)
* Поиск существ с определёнными типами восприятия (например, которые видят в темноте)
* Генерация случайной встречи по фильтрам

---

## Рекомендации

* Делать поля максимально атомарными (например: скорость отдельно для каждого типа перемещения).
* Использовать теги для условий и эффектов.
* Добавить возможность экспорта/импорта пользовательских монстров и заклинаний.
* Сделать поиск по ключевым словам внутри описаний.

---

## JSON-схемы и примеры

### Monster (schema)

```json
{
  "type": "object",
  "required": ["name", "type", "size", "alignment", "ac", "hp", "cr", "abilities"],
  "properties": {
    "name": {"type": "string"},
    "type": {"type": "string"},
    "size": {"type": "string", "enum": ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]},
    "alignment": {"type": "string"},
    "ac": {"type": "integer", "minimum": 0},
    "hp": {"type": "integer", "minimum": 0},
    "hit_dice": {"type": "string"},
    "speeds": {
      "type": "object",
      "properties": {
        "walk": {"type": "integer"},
        "fly": {"type": "integer"},
        "swim": {"type": "integer"},
        "climb": {"type": "integer"},
        "burrow": {"type": "integer"}
      },
      "additionalProperties": false
    },
    "cr": {"type": ["number", "string"]},
    "xp": {"type": "integer"},
    "proficiency_bonus": {"type": "integer"},
    "abilities": {
      "type": "object",
      "required": ["str", "dex", "con", "int", "wis", "cha"],
      "properties": {
        "str": {"type": "integer"},
        "dex": {"type": "integer"},
        "con": {"type": "integer"},
        "int": {"type": "integer"},
        "wis": {"type": "integer"},
        "cha": {"type": "integer"}
      }
    },
    "saving_throws": {"type": "object", "additionalProperties": {"type": "integer"}},
    "skills": {"type": "object", "additionalProperties": {"type": "integer"}},
    "senses": {
      "type": "object",
      "properties": {
        "passive_perception": {"type": "integer"},
        "darkvision": {"type": "integer"},
        "blindsight": {"type": "integer"},
        "tremorsense": {"type": "integer"},
        "truesight": {"type": "integer"}
      },
      "additionalProperties": false
    },
    "languages": {"type": "array", "items": {"type": "string"}},
    "damage_immunities": {"type": "array", "items": {"type": "string"}},
    "damage_resistances": {"type": "array", "items": {"type": "string"}},
    "damage_vulnerabilities": {"type": "array", "items": {"type": "string"}},
    "condition_immunities": {"type": "array", "items": {"type": "string"}},
    "traits": {
      "type": "array",
      "items": {"type": "object", "properties": {"name": {"type": "string"}, "desc": {"type": "string"}}}
    },
    "actions": {
      "type": "array",
      "items": {"type": "object", "properties": {"name": {"type": "string"}, "desc": {"type": "string"}}}
    },
    "reactions": {
      "type": "array",
      "items": {"type": "object", "properties": {"name": {"type": "string"}, "desc": {"type": "string"}}}
    },
    "legendary_actions": {
      "type": "array",
      "items": {"type": "object", "properties": {"name": {"type": "string"}, "desc": {"type": "string"}}}
    },
    "spellcasting": {
      "type": "object",
      "properties": {
        "ability": {"type": "string"},
        "dc": {"type": "integer"},
        "attack_bonus": {"type": "integer"},
        "at_will": {"type": "array", "items": {"type": "string"}},
        "per_day": {"type": "object", "additionalProperties": {"type": "array", "items": {"type": "string"}}},
        "spells": {"type": "array", "items": {"type": "string"}}
      }
    },
    "tags": {"type": "array", "items": {"type": "string"}}
  },
  "additionalProperties": false
}
```

### Monster (example)

```json
{
  "name": "Goblin",
  "type": "humanoid (goblinoid)",
  "size": "Small",
  "alignment": "neutral evil",
  "ac": 15,
  "hp": 7,
  "hit_dice": "2d6 - 2",
  "speeds": {"walk": 30},
  "cr": 0.25,
  "xp": 50,
  "proficiency_bonus": 2,
  "abilities": {"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8},
  "skills": {"Stealth": 6},
  "senses": {"passive_perception": 9, "darkvision": 60},
  "languages": ["Common", "Goblin"],
  "traits": [{"name": "Nimble Escape", "desc": "The goblin can take the Disengage or Hide action as a bonus action on each of its turns."}],
  "actions": [{"name": "Scimitar", "desc": "+4 to hit, 5 ft., one target. Hit: 5 (1d6+2) slashing."}],
  "reactions": [],
  "legendary_actions": [],
  "spellcasting": null,
  "tags": ["low-cr", "skirmisher"]
}
```

### Spell (schema)

```json
{
  "type": "object",
  "required": ["name", "school", "level", "casting_time", "range", "duration", "components", "description"],
  "properties": {
    "name": {"type": "string"},
    "school": {"type": "string"},
    "level": {"type": "integer", "minimum": 0, "maximum": 9},
    "ritual": {"type": "boolean"},
    "casting_time": {"type": "string"},
    "range": {"type": "string"},
    "duration": {"type": "string"},
    "concentration": {"type": "boolean"},
    "components": {
      "type": "object",
      "properties": {
        "v": {"type": "boolean"},
        "s": {"type": "boolean"},
        "m": {"type": "boolean"},
        "material_desc": {"type": "string"}
      },
      "required": ["v", "s", "m"],
      "additionalProperties": false
    },
    "classes": {"type": "array", "items": {"type": "string"}},
    "description": {"type": "string"},
    "damage": {
      "type": "object",
      "properties": {
        "dice": {"type": "string"},
        "type": {"type": "string"},
        "scaling_by_slot": {"type": "object", "additionalProperties": {"type": "string"}}
      }
    },
    "saving_throw": {"type": "object", "properties": {"ability": {"type": "string"}, "effect": {"type": "string"}}},
    "area": {"type": "object", "properties": {"shape": {"type": "string"}, "size": {"type": "integer"}}},
    "conditions": {"type": "array", "items": {"type": "string"}},
    "tags": {"type": "array", "items": {"type": "string"}}
  },
  "additionalProperties": false
}
```

### Spell (example)

```json
{
  "name": "Fireball",
  "school": "Evocation",
  "level": 3,
  "ritual": false,
  "casting_time": "1 action",
  "range": "150 feet",
  "duration": "Instantaneous",
  "concentration": false,
  "components": {"v": true, "s": true, "m": true, "material_desc": "A tiny ball of bat guano and sulfur"},
  "classes": ["Wizard", "Sorcerer"],
  "description": "A bright streak flashes... then blossoms with a low roar into an explosion of flame.",
  "damage": {"dice": "8d6", "type": "fire", "scaling_by_slot": {"4": "9d6", "5": "10d6"}},
  "saving_throw": {"ability": "Dexterity", "effect": "half on success"},
  "area": {"shape": "sphere", "size": 20},
  "conditions": ["ignites objects"],
  "tags": ["aoe", "damage"]
}
```
