# 📂 Структура проекта V6

## ✅ АКТИВНАЯ ВЕРСИЯ: V6 (CoT Reasoning + KB Fallback)

### Основные файлы (корневая директория):
```
Перед 0_2/
├── web_app_v6_cot_fallback.py  ← ГЛАВНЫЙ ФАЙЛ (анализатор)
├── web_server_v6.py            ← Сервер (порт 5006)
├── start_v6.sh                 ← Скрипт запуска
├── knowledge_base.json         ← База знаний (49 entries)
├── MEMORY.md                   ← Долгосрочная память
│
├── AGENTS_RULES/               ← Правила для агентов
│   ├── PROJECT_MEMORY.md       ← История проекта
│   ├── rules_general.md
│   ├── session_handover.md
│   └── shared_status.md
│
├── archive/                    ← Архив старых версий
│   ├── old_versions/           ← V4, V5, fix_*.py
│   ├── tests/                  ← test_*.py, benchmark_*.py
│   ├── scripts/                ← create_kb.py, patch_*.py
│   ├── docs/                   ← VERSION_HISTORY.md, *_GUIDE.md
│   ├── logs/                   ← *.log
│   └── temp/                   ← временные файлы
│
├── Перед 0/                    ← Исходные документы
│   ├── Isxodnie_documenti/     ← Пакеты 1, 2, 4
│   └── 12 правильных ответов/  ← Эталоны + сканы
│
└── output/                     ← Результаты анализа
```

---

## 🚀 Быстрый старт

### Запуск сервера:
```bash
cd /home/segun/CascadeProjects/Перед\ 0_2
bash start_v6.sh
```

**Адрес**: http://172.31.130.149:5006

### Остановка сервера:
```bash
pkill -f web_server_v6.py
```

### Просмотр логов:
```bash
tail -f v6_server.log
```

---

## 📊 Версии проекта

| Версия | Расположение | Статус |
|--------|-------------|--------|
| **V6** | `web_app_v6_cot_fallback.py` | ✅ **АКТИВНАЯ** |
| V5_vostok | `archive/old_versions/web_app_v5_vostok.py` | 📦 Архив |
| V5_final | `archive/old_versions/web_app_v5_final.py` | 📦 Архив |
| V4_optimized | `archive/old_versions/web_app_v4_optimized.py` | 📦 Архив |

---

## 🎯 Особенности V6

### 1. CoT (Chain-of-Thought) - 7 шагов анализа:
- ШАГ 1: ОПРЕДЕЛИ ТИП ДОКУМЕНТА
- ШАГ 2: НАЙДИ ЗАКАЗЧИКА (маркеры: "Заказчик:", "Администрация")
- ШАГ 3: НАЙДИ РАЗРАБОТЧИКА (маркеры: "ИП", "ООО")
- ШАГ 4: ИЗВЛЕКИ ГОД (шифр /25 → 2025)
- ШАГ 5: СОБЕРИ НАЗВАНИЕ
- ШАГ 6: ОПИШИ СОДЕРЖАНИЕ
- ШАГ 7: СФОРМУЛИРУЙ ЦЕЛЬ

### 2. Fallback на KB структуру:
Если документ НЕ похож на примеры → используй структуру как шаблон

### 3. KB Override:
Если score > 0.75 → использовать данные из KB (100% точность)

### 4. Улучшенный Semantic Matching:
- Проверка схожести по тексту
- Приоритет по номеру раздела
- Boost для шифров

---

## 📝 Текущие результаты

**Точность**: 75-85% (ожидаемая)
**Время**: 2-4 сек/файл
**KB loaded**: 49 entries

---

## 🔧 Технические детали

### API Endpoint:
- **URL**: http://192.168.47.22:1234/v1/chat/completions
- **Модель**: `mistralai/ministral-3-14b-reasoning`
- **Max tokens**: 3000
- **Temperature**: 0.1

### Извлекаемые поля:
1. title - Название документа
2. customer - Заказчик
3. developer - Разработчик
4. year - Год составления
5. document_type - Тип документа
6. content_summary - Содержание
7. purpose - Цель

---

## 📂 Архив

### old_versions/
- `web_app_v5_vostok.py` - стабильная V5
- `web_app_v5_final.py` - финальная V5
- `web_app_v4_optimized.py` - оптимизированная V4
- `fix_v1_simple.py` - простое исправление
- `fix_v2_robust_json.py` - улучшенный JSON-парсер
- `fix_v3_hybrid.py` - гибридный подход

### tests/
- `benchmark_models.py` - массовый бенчмарк
- `test_v6_llm.py` - тест LLM API
- `check_accuracy.py` - проверка точности

### scripts/
- `create_kb.py` - генератор Knowledge Base
- `patch_analyzer.py` - патч для анализатора
- `update_kb.py` - обновление KB

### docs/
- `VERSION_HISTORY.md` - история версий
- `VERSION_SWITCH_GUIDE.md` - инструкция переключения
- `IMPROVEMENT_GUIDE.md` - руководство улучшений

---

## 🎯 Следующие шаги

1. ✅ V6 очищена от старых версий
2. 🔄 Протестировать на реальных документах
3. 📊 Запустить бенчмарк: `python3 archive/tests/benchmark_models.py`
4. 🎯 Если точность < 75% → проверить DeepSeek R1

---

## 📞 Поддержка

**Логи**: `tail -f v6_server.log`
**Документация**: `archive/docs/`
**История**: `AGENTS_RULES/PROJECT_MEMORY.md`
