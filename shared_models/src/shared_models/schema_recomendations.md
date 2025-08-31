Монстры — поля под фильтры/генерацию
Обязательные (индексировать)

name_ru (str, index) — русское имя.

name_en (str, index) — для сопоставления с источниками.

type (enum: aberration/fiend/undead/...; index)

size (enum: Tiny/Small/Medium/Large/Huge/Gargantuan; index)

alignment (enum или нормализованная строка; index)

cr (numeric; index) — основа бюджета энкаунтера.

ac (int; index)

hp (int; index)

speeds (JSONB: {walk, fly, swim, climb, burrow}) — хранение;
добавить derived: speed_walk, speed_fly, … (int; index) для быстрых фильтров.

Сильно рекомендуемые для фильтрации

subtypes (ARRAY[str]; index) — например: goblinoid, shapechanger, swarm.

languages (ARRAY[str]; index)

senses (JSONB) + derived-флаги: has_darkvision (bool; index), has_blindsight, has_truesight, tremorsense_range (int).

damage_immunities (ARRAY[str]; index)

damage_resistances (ARRAY[str]; index)

damage_vulnerabilities (ARRAY[str]; index)

condition_immunities (ARRAY[str]; index)

environments (ARRAY[enum]: arctic, desert, forest, grassland, mountain, swamp, coast, underdark, urban, planar; index)
→ Очень полезно для генераторов по биому.

roles (ARRAY[enum]: brute, skirmisher, artillery, controller, lurker, support, solo; index)
→ Удобные «боевые роли» для автоподбора состава.

is_legendary (bool; index)

has_lair_actions (bool; index)

is_spellcaster (bool; index) + spellcasting_ability (enum: INT/WIS/CHA; index)

source (enum/str: MM, VGM, MToF, SRD, HB; index) + page (int) — отслеживание происхождения.

tags (ARRAY[str]; index) — любые доп. теги для пресетов.

Для генератора энкаунтеров (derived/служебные)

xp (int) — прямая таблица XP по CR удобна в БД.

offensive_cr_hint (numeric) — по оценке DPT/атакам (если не считаешь — поле можно оставить null).

defensive_cr_hint (numeric) — по AC/HP/resist.

is_flying (bool; index) — из speeds.fly > 0.

has_ranged (bool; index) — парс экшенов; полезно.

has_aoe (bool; index) — парс экшенов/заклинаний на AOE.

threat_tier (smallint; index) — группировка CR (например: 0–1/8/1/4/1/2 → tier 0, 1–4 → tier1, 5–10 → tier2, 11–16 → tier3, 17+ → tier4).

party_level_min / party_level_max (smallint; index) — эвристический диапазон уровней для fair/hard (необязательно, но ускоряет пресеты).

Текстовые блоки (в JSONB, без индексов или с GIN при необходимости)

traits (JSONB[{name, desc}])

actions (JSONB[{name, desc}])

reactions (JSONB[{name, desc}])

legendary_actions (JSONB[{name, desc}])

lair_actions (JSONB[{name, desc}])

regional_effects (JSONB[{name, desc}])

spellcasting (JSONB) — {ability, dc, attack_bonus, at_will[], per_day{1/day:[],…}, spell_list[]}

description (TEXT)

Индексы: GIN на массивы/JSONB (btree + gin_trgm для поиска по имени), btree на CR/AC/HP/size/type.

Заклинания — поля под фильтры/генерацию
Обязательные (индексировать)

name_ru (str; index)

name_en (str; index)

school (enum; index)

level (smallint 0–9; index)

casting_time (enum/str нормализованное: action, bonus_action, reaction, minute_1, minute_10, hour_1; index)

range (str нормализованный + derived range_feet int; index)

duration (str нормализованный + is_concentration bool; index)

components (JSONB {v:bool, s:bool, m:bool, material_desc:str, gp_cost:int|null, consumed:bool|null})

classes (ARRAY[enum CasterClass]; index)

Сильно рекомендуемые (фильтры по боевой роли/утилите)

targeting (enum: self, creature, creatures, object, point, line, cone, cube, sphere, cylinder; index)

area_shape (enum) + area_size (int) — для AOE-фильтров.

damage (JSONB {type:str, dice:str, scaling_by_slot:{4:"…"}}) + damage_type (enum; index)

save (enum ability: STR/DEX/CON/INT/WIS/CHA; index) + save_effect (enum: half, negate, partial)

attack_roll (bool; index) — заклинание требует spell attack вместо сейва.

conditions (ARRAY[enum]: blinded, charmed, frightened, prone, restrained, paralyzed, stunned, etc.; index)

ritual (bool; index)

tags (ARRAY[str]; index) — роли: damage, control, debuff, buff, heal, summon, utility, mobility, defense, dispel, divination.

Текст/описание

description (TEXT/JSONB blocks)

source (enum/str; index), page (int)

Мини-правки к твоей схеме (SQLModel)
Monster

Убери speed: int; оставь только speeds: JSONB и добавь плоские derived:

speed_walk, speed_fly, speed_swim, speed_climb, speed_burrow (int; nullable; index).
Это сильно ускорит фильтры «нужен летающий» и т. п.

Добавь:

subtypes: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()), index=True)
environments: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()), index=True)
roles: Optional[List[str]] = Field(default=None, sa_type=ARRAY(String()), index=True)
is_legendary: Optional[bool] = Field(default=None, index=True)
has_lair_actions: Optional[bool] = Field(default=None, index=True)
is_spellcaster: Optional[bool] = Field(default=None, index=True)
source: Optional[str] = Field(default=None, index=True)
page: Optional[int] = Field(default=None)
# derived fast flags:
is_flying: Optional[bool] = Field(default=None, index=True)
has_ranged: Optional[bool] = Field(default=None, index=True)
has_aoe: Optional[bool] = Field(default=None, index=True)
threat_tier: Optional[int] = Field(default=None, index=True)


Локализация:

name_ru: Optional[str] = Field(default=None, index=True)
name_en: Optional[str] = Field(default=None, index=True)
slug: Optional[str] = Field(default=None, index=True)


senses разложить частично на derived:

has_darkvision: Optional[bool] = Field(default=None, index=True)
darkvision_range: Optional[int] = Field(default=None)
has_blindsight: Optional[bool] = Field(default=None, index=True)
blindsight_range: Optional[int] = Field(default=None)
has_truesight: Optional[bool] = Field(default=None, index=True)
truesight_range: Optional[int] = Field(default=None)
tremorsense_range: Optional[int] = Field(default=None, index=True)


Оставь текстовые блоки (traits/actions/...) в JSONB как есть — они не для массовых индексов.

Spell

У тебя уже есть range — удали distance (дублирование и менее универсально).

Нормализуй и добавь поля под фильтры:

is_concentration: Optional[bool] = Field(default=None, index=True)  # дубль из duration, но быстрый фильтр
ritual: Optional[bool] = Field(default=None, index=True)
targeting: Optional[str] = Field(default=None, index=True)
area: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSONB)  # {shape, size}
attack_roll: Optional[bool] = Field(default=None, index=True)
damage_type: Optional[str] = Field(default=None, index=True)  # дубль из JSONB damage, но быстрый фильтр
save_ability: Optional[str] = Field(default=None, index=True)  # дубль из saving_throw
source: Optional[str] = Field(default=None, index=True)
page: Optional[int] = Field(default=None)
name_ru: Optional[str] = Field(default=None, index=True)
name_en: Optional[str] = Field(default=None, index=True)
slug: Optional[str] = Field(default=None, index=True)


components расширить: gp_cost (int), consumed (bool).

Приведи casting_time к конечному набору (action/bonus/reaction/1m/10m/1h/8h), иначе фильтры страдают.

Добавь tags (боевые роли/утилита) как у монстров — это резко упрощает сценарные подборки.

Индексация и производительность

btree: cr, ac, hp, size, type, is_flying, is_legendary, is_spellcaster, threat_tier, level, school, is_concentration, ritual, damage_type, save_ability.

GIN по ARRAY: languages, damage_*, condition_immunities, environments, roles, classes, tags.

GIN jsonb_path_ops по speeds, senses, components, damage, area, saving_throw, если будут сложные запросы.

trigram (pg_trgm) на name_ru, name_en для «как называется то заклинание про…».

Мини-итог (что точно оставить/добавить)

Оставить и индексировать: type, size, alignment, cr, ac, hp, languages, все «иммунитеты/резисты/уязвимости/conditions, environments, roles, is_legendary, is_spellcaster, speeds+ плоскиеspeed_*`.

Добавить для генераторов: is_flying, has_ranged, has_aoe, threat_tier.

По заклинаниям: level, school, casting_time (нормализ.), range (+ range_feet), duration (+ is_concentration), components (+ gp_cost, consumed), classes, damage_type, save_ability, targeting, area_shape/area_size, tags.

Локализация/источник: name_ru, name_en, source, page, slug.