# ИСТОРИЯ ВЕРСИЙ web_app

## web_app_v5.py (ОРИГИНАЛ - РАБОЧАЯ)
**Что делала:**
- `_get_semantic_examples()` - подбор примеров из KB по токенам
- LLM вызов с примерами
- Простая логика без boost'ов
- **100% точность на тесте 07.04.2026**

**Где находится:** недоступна (в папке project_analyzer)

---

## web_app_v5_llm.py (ТЕКУЩАЯ РАБОЧАЯ)
**Что делает:**
- Полный веб-сервер на Flask
- `_get_semantic_examples()` - подбирает до 3 примеров из KB по пересечению токенов
- LLM вызов через LM Studio API
- Поддержка PDF/DOCX/XML
- Порт: 5002

**Статус:** ✅ РАБОТАЕТ

---

## web_app_v5_final.py (СЛОМАННАЯ)
**Что я делал:**
1. Добавил `_calculate_score()` с boost'ами
2. Добавил `_get_kb_matching_entries()`
3. Добавил `_get_kb_direct_fields()`
4. Добавил приоритет по шифру (157/25, МКД-0109)
5. Boost'ы: АР/КР/ПБ → 75%, ИОС5.3 → 95%

**Что сломалось:**
- KB override не срабатывал (пересчёт score без boost'ов)
- Matching находил неправильные записи (МЕС-БМК вместо 157/25)
- Поля content_summary и purpose были пустыми

**Статус:** ❌ СЛОМАНА (сохранена как web_app_v5_final_broken.py)

---

## web_server.py (v6.1)
**Что делал:**
- Добавил индикатор KB override
- Badge: ✓/⚠/✗
- Score в %
- Топ-2 примера для LLM

**Проблема:** вызывает `_get_kb_matching_entries()` которой нет в web_app_v5_llm.py

---

## РЕШЕНИЕ
**Текущая рабочая версия:** web_app_v5_llm.py
**Порт:** 5002
**Как запустить:** 
```bash
screen -dmS web_server python3 .kilo/worktrees/playful-flower/web_app_v5_final.py
```

---

## ЧТО НУЖНО СДЕЛАТЬ
1. Взять оригинальный web_app_v5.py из project_analyzer
2. Скопировать в .kilo/worktrees/playful-flower/web_app_v5_final.py
3. Перезапустить сервер на порту 5002
