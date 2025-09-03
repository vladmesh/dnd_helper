## Bot/API i18n plan — iterative increments

Goal: all bot UI и API ответы строго следуют выбранному `users.lang`, с корректным фолбэком. Работы разбиты на независимые инкременты; каждый инкремент приносит ценность и может быть отдельно задеплоен.

### Iteration 0 — Baseline audit (done)

- Бот местами берёт язык из `update.effective_user.language_code` вместо `users.lang`.
- Хардкоды на русском в `dice.py`, промпты поиска в `monsters.py`/`spells.py`, `Settings:` в `menu.py`.
- Поиск в боте не передаёт `lang`; `/monsters/search` и `/spells/search` на бэке не локализуют.
- Лейблы через labeled-ручки корректны при передаче `lang`.

### Iteration 1 — Единый источник языка в боте (done)

- Правило: если пользователь зарегистрирован, используем только `user.lang`; иначе — телеграмный `language_code` как временный фолбэк.
- Внедрить функцию получения языка пользователя: `get_user_lang(tg_user) -> ru|en` с кэшом в `context.user_data`.
- Применить в:
  - `handlers/menu.py`: все места, где сейчас читается `language_code`.
  - `handlers/monsters.py`, `handlers/spells.py`: заменить `_detect_lang` на использование `get_user_lang`.
- Без замены текстов и без добавления новых API — только источник языка.
- Acceptance: все существующие тексты переключаются корректно по `user.lang` (там где уже есть i18n ветки).

### Iteration 2 — Локализация поиска в API (done)

- `GET /monsters/search`: добавить `lang: Optional[str]` и применять `_apply_monster_translations_bulk`, выставлять `Content-Language`.
- `GET /spells/search`: аналогично через `_apply_spell_translations_bulk`.
- Бот: в `handlers/search.py` добавлять `params={"lang": get_user_lang(...)}`.
- Acceptance: результаты поиска возвращаются с локализованными `name/description` и согласуются с `user.lang`.

### Iteration 3 — Вынесение UI-строк в БД (новая таблица + API) (done)

- Модель `UiTranslation` (наследует `BaseModel`, поля `created_at`, `updated_at` унаследованы):
  - `id` (PK)
  - `namespace: str` (например, `bot`)
  - `key: str` (например, `menu.main.title`)
  - `lang: Language` (`ru` | `en`)
  - `text: str`
  - Unique: `(namespace, key, lang)`
- API: `GET /i18n/ui?ns=bot&lang=ru|en` → `{ key: text }` с фолбэком RU↔EN по аналогии с `resolve_enum_labels`.
- Сидирование: первичные строки из текущих хардкодов обоих языков.
- Acceptance: ручка отдаёт полный набор ключей для namespace, `Content-Language` соответствует.

### Iteration 4 — Интеграция бота с БД-текстами

- Клиент в боте: кэшировать на процесс `{lang -> {ns -> {key:text}}}`; функция `t(key, lang, default=None)`.
- Точечные замены хардкодов на `t(...)` в критичных местах:
  - `handlers/dice.py`: все подписи/промпты/ошибки/заголовки.
  - `handlers/monsters.py`/`handlers/spells.py`: промпты поиска, пустые списки, навигация.
  - `handlers/menu.py`: `Settings:` и заголовки меню.
- Acceptance: все ранее отмеченные хардкоды теперь приходят из БД и корректно меняются по `user.lang`.

### Iteration 5 — Единообразная передача языка в API

- В `api_client` добавить опциональную установку заголовка `Accept-Language` в дополнение к `lang` в query (без изменения текущих контрактов).
- Унифицировать вызовы API из бота: всегда передавать `lang` из `get_user_lang` и ставить заголовок.
- Acceptance: заголовок и query в логе запросов соответствуют `user.lang` для всех вызовов.

### Notes

- Фолбэк переводов остаётся симметричным (RU↔EN), как сейчас для enum labels.
- `updated_at`/`created_at` берутся из базового класса `BaseModel` и не дублируются в `UiTranslation`.



