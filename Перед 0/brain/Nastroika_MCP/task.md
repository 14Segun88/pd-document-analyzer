# Текущая задача

---

## Активная задача

**Подгрузить блокноты из MCP сервера NotebookLM: "Структура работы отдела приемки"**

### Статус выполнения

| Шаг | Статус |
|-----|--------|
| Установка `uv` | ✅ Выполнено |
| Установка `notebooklm-mcp-cli` | ✅ Выполнено |
| Установка Playwright + Chromium | ✅ Выполнено |
| Авторизация через Google (nlm login) | ✅ Выполнено |
| Добавление в mcp_config.json | ✅ Выполнено |
| Проверка подключения (nlm doctor) | ✅ Выполнено |
| **Получение списка инструментов** | ✅ Выполнено |
| **Подгрузить блокноты в Brain** | ✅ Выполнено (Структура_работы_отдела_приемки_Источники.md) |

---

## Доступные инструменты MCP

**Блокноты:** `notebook_list`, `notebook_create`, `notebook_get`, `notebook_delete`  
**Источники:** `source_add`, `source_get_content`, `source_list_drive`  
**Студия:** `studio_create`, `studio_status` (аудио/видео)  
**Запросы:** `notebook_query`, `cross_notebook_query`, `chat_configure`  
**Дополнительно:** `research_start`, `download_artifact`, `note`, `batch`

---

## Следующий шаг

Вызвать `notebook_list` для получения списка блокнотов и найти "Структура работы отдела приемки"
