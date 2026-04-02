# План реализации

---

## Этап 1: Установка и настройка ✅

| Шаг | Команда | Статус |
|-----|---------|--------|
| Установка uv | `pip install uv` | ✅ |
| Установка notebooklm-mcp-cli | `pip install notebooklm-mcp-cli` | ✅ |
| Установка Playwright | `~/.local/bin/uvx playwright install chromium` | ✅ |
| Создание симлинков браузера | `ln -sf ~/.cache/ms-playwright/.../chrome ~/.local/bin/google-chrome` | ✅ |

---

## Этап 2: Авторизация ✅

| Шаг | Команда | Статус |
|-----|---------|--------|
| Проверка окружения | `nlm doctor` | ✅ |
| Авторизация Google | `nlm login` | ✅ |
| Вход пользователя в браузере | Chromium открылся | ✅ |
| Сохранение ключей | Профиль `default` | ✅ |

---

## Этап 3: Конфигурация MCP ✅

| Файл | Изменение | Статус |
|------|-----------|--------|
| `~/.gemini/antigravity/mcp_config.json` | Добавлен сервер notebooklm-mcp | ✅ |

---

## Этап 4: Использование MCP ⏳

### Доступные инструменты

**Блокноты:**
- `notebook_list` — получить список блокнотов
- `notebook_create` — создать новый блокнот
- `notebook_get` / `notebook_describe` — получить инфо
- `notebook_rename` / `notebook_delete` — управление

**Источники:**
- `source_add` / `source_delete` — добавить/удалить источник
- `source_get_content` — прочитать содержимое с цитатами
- `source_list_drive` / `source_sync_drive` — Google Drive

**Студия:**
- `studio_create` — генерация аудиоподкаста
- `studio_status` — проверить готовность
- `studio_revise` / `studio_delete` — управление

**Запросы:**
- `notebook_query` — вопрос к блокноту
- `cross_notebook_query` — вопрос по нескольким блокнотам
- `chat_configure` — настройка промпта

**Дополнительно:**
- `research_start` / `research_import` — сбор информации
- `download_artifact` / `export_artifact` — выгрузка
- `note` — заметки
- `batch` / `pipeline` — массовые операции

---

## Текущая задача

**Запрос:** Подгрузить блокноты из MCP сервера NotebookLM "Структура работы отдела приемки"

### План действий

| # | Действие | Инструмент |
|---|----------|------------|
| 1 | Получить список блокнотов | `notebook_list` |
| 2 | Найти блокнот "Структура работы отдела приемки" | — |
| 3 | Получить содержимое блокнота | `notebook_get` / `source_get_content` |
| 4 | Сохранить в Brain | Создать файл в `brain/` |

---

## Команды для работы

```bash
# Проверка статуса
~/.local/bin/uvx --from notebooklm-mcp-cli nlm doctor

# Справка
~/.local/bin/uvx --from notebooklm-mcp-cli nlm --help
```

---

## Результат

✅ NotebookLM MCP Server установлен, настроен и готов к работе  
⏳ Ожидается выполнение запроса по блокноту "Структура работы отдела приемки"
