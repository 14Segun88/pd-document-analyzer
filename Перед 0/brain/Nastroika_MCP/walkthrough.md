# Walkthrough — История настройки NotebookLM MCP

---

## Запрос пользователя

> Установи и настрой NotebookLM MCP server для меня. Используй самый удобный способ (uvx или pip). Авторизуйся через браузер, добавь его в mcp_config.json и проверь подключение. Покажи список доступных инструментов после настройки.

---

## Выполненные шаги

### 1. Поиск и установка

| Действие | Команда |
|----------|---------|
| Проверка pipx/pip | `pipx --version \|\| pip --version` |
| Установка uv | `pip install uv` |
| Установка notebooklm-mcp-cli | `pip install notebooklm-mcp-cli` |
| Проверка uvx | `~/.local/bin/uvx --from notebooklm-mcp-cli notebooklm-mcp --help` |

### 2. Настройка авторизации

| Действие | Команда |
|----------|---------|
| Проверка nlm | `~/.local/bin/uvx --from notebooklm-mcp-cli nlm --help` |
| Проверка окружения | `nlm doctor` |
| Установка Playwright + Chromium | `~/.local/bin/uvx playwright install chromium` |
| Создание симлинков браузера | `ln -sf ~/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome ~/.local/bin/google-chrome` |

### 3. Авторизация через Google

| Действие | Результат |
|----------|-----------|
| Запуск авторизации | `nlm login` |
| Открытие браузера Chromium | Пользователь вошёл в Google |
| Сохранение ключей | Профиль `default` авторизован |

### 4. Добавление в конфигурацию

| Файл | Изменение |
|------|-----------|
| `~/.gemini/antigravity/mcp_config.json` | Добавлен сервер notebooklm-mcp |

### 5. Проверка подключения

| Проверка | Результат |
|----------|-----------|
| `nlm doctor` | ✅ Успешно |
| Получение списка инструментов | ✅ 20+ инструментов |

---

## Доступные инструменты MCP

### Блокноты (Notebooks)
- `notebook_list` — получить список блокнотов
- `notebook_create` — создать новый блокнот
- `notebook_get` / `notebook_describe` — получить инфо/описание
- `notebook_rename` / `notebook_delete` — переименовать/удалить

### Источники (Sources)
- `source_add` / `source_delete` — добавить/удалить источник
- `source_get_content` — прочитать содержимое с цитатами
- `source_list_drive` / `source_sync_drive` — Google Drive
- `source_describe` / `source_rename` — саммари/переименовать

### Студия (Studio)
- `studio_create` — генерация аудиоподкаста (Audio Overview)
- `studio_status` — проверить готовность
- `studio_revise` / `studio_delete` — переделать/удалить

### Запросы (Chat/Query)
- `notebook_query` — вопрос к конкретному блокноту
- `cross_notebook_query` — вопрос по нескольким блокнотам
- `chat_configure` — настройка системного промпта

### Дополнительно
- `research_start` / `research_import` — сбор информации
- `download_artifact` / `export_artifact` — выгрузка результатов
- `note` — текстовые заметки
- `batch` / `pipeline` — массовые операции

---

## Последний запрос пользователя

> подгрузи в Brain блокноты из MCP сервера NotebookLM "Структура работы отдела приемки"

**Статус:** ✅ Выполнено.
Ноутбук `Структура работы - отдел приемки - 8 шагов` был найден, и содержимое всех 13 источников успешно выгружено в файл `brain/Структура_работы_отдела_приемки_Источники.md`.
