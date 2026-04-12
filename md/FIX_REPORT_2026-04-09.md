# 🔧 ИСПРАВЛЕНИЕ АЛГОРИТМА _calculate_score

## 📋 Описание проблемы

### Симптомы
- Документы проекта **МКД-0109-2024-ПИР** ошибочно матчатся с проектом **МЕС-БМК-04/24**
- Пример: `Раздел_ПД№9_МКД-0109-2024-ПИР-ПБ` → совпадает с `Раздел 9 (МЕС-БМК-04/24-ПБ)` ❌
- Результат: неправильные `document_type`, `content_summary`, `purpose`

### Корневая причина

Алгоритм `_calculate_score()` в `v6/web_app_v6_cot_fallback.py`:

```python
# СТАРЫЙ КОД (строки 92-100)
file_section = re.search(r'ПД№(\d+)', filename)
kb_section = re.search(r'Раздел\s*(\d+)', kb_title)
if file_section and kb_section and file_section.group(1) == kb_section.group(1):
    score = max(score, 0.99)  # ← BOOST ПО РАЗДЕЛУ (игнорирует шифр!)

file_code = self._extract_code_from_filename(filename)
kb_code = self._extract_code_from_filename(kb_title)
if file_code and kb_code and file_code == kb_code:
    score = max(score, 0.85)  # ← BOOST ПО ШИФРУ (НИЖЕ приоритет!)
```

**Проблема**: 
1. При совпадении раздела (ПД№9 == Раздел 9) устанавливается score=0.99
2. При совпадении шифра устанавливается score=0.85
3. Boost по разделу **перекрывает** boost по шифру
4. KB Override threshold = 0.90 → срабатывает при boost по разделу

---

## ✅ Решение

### 1. Исправление алгоритма `_calculate_score`

**Новый код**:

```python
def _calculate_score(self, filename, kb_title):
    from difflib import SequenceMatcher
    score = SequenceMatcher(None, filename.lower(), kb_title.lower()).ratio()

    file_section = re.search(r'ПД№(\d+)', filename)
    kb_section = re.search(r'Раздел\s*(\d+)', kb_title)
    file_code = self._extract_code_from_filename(filename)
    kb_code = self._extract_code_from_filename(kb_title)

    # Нормализация шифров (МЕС-БМК-04/24 → МЕС-БМК-04-24)
    if file_code:
        file_code = file_code.replace('/', '-')
    if kb_code:
        kb_code = kb_code.replace('/', '-')

    # BOOST ПО РАЗДЕЛУ С ПРОВЕРКОЙ ШИФРА
    if file_section and kb_section and file_section.group(1) == kb_section.group(1):
        if file_code and kb_code and file_code == kb_code:
            score = max(score, 0.99)  # Раздел И шифр совпали
        else:
            score = max(score, 0.70)  # Только раздел (ниже приоритет)

    if file_code and kb_code and file_code == kb_code:
        score = max(score, 0.90)  # Только шифр

    if 'АР' in filename and 'АР' in kb_title: score = max(score, 0.75)
    if 'КР' in filename and 'КР' in kb_title: score = max(score, 0.75)
    if 'ПБ' in filename and ('ПБ' in kb_title or 'пожарн' in kb_title.lower()): score = max(score, 0.85)
    if 'ОДИ' in filename and 'ОДИ' in kb_title: score = max(score, 0.85)

    return score
```

### 2. Улучшенное извлечение шифров

**Новый метод `_extract_code_from_filename`**:

```python
def _extract_code_from_filename(self, filename):
    # Паттерн 1: МКД-0109-2024
    match = re.search(r'([А-Я]{2,4}-\d{4}-\d{4})', filename)
    if match:
        return match.group(1)
    # Паттерн 2: МЕС-БМК-04/24, МЕС-БМК-04_24, МЕС-БМК-04.24
    match = re.search(r'([А-Я]{2,4}-[А-Я]{2,4}[\-_\.]\d{2}[\-_\.]\d{2})', filename)
    if match:
        return match.group(1).replace('_', '-').replace('.', '-')
    # Паттерн 3: МЕС_БМК_04_24
    match = re.search(r'([А-Я]{2,4}_[А-Я]{2,4}_\d{2}_\d{2})', filename)
    if match:
        return match.group(1).replace('_', '-')
    # Паттерн 4: МЕС-БМК-04/24 (из KB)
    match = re.search(r'([А-Я]{2,4}-[А-Я]{2,4}-\d{2}/\d{2})', filename)
    if match:
        return match.group(1)
    # Паттерн 5: 157/25, 04/24
    match = re.search(r'(\d{2,4}/\d{2,4})', filename)
    if match:
        return match.group(1)
    return None
```

### 3. Удаление дубликатов из KB

**Проблема**: В KB было 61 запись, из них 13 дубликатов.

**Решение**: Создан скрипт `remove_kb_duplicates.py`

**Результат**: KB сокращён до 48 записей.

---

## 📊 Результаты тестирования

### До исправления

```
📄 Раздел_ПД№9_МКД-0109-2024-ПИР-ПБ_вер.01 (2).pdf
   KB: Раздел 9 (МЕС-БМК-04/24-ПБ)
   Шифр файла: МКД-0109-2024
   Шифр KB:    04/24
   Совпадение: ❌
   SCORE: 0.99 ✅ KB Override ← ОШИБКА!
```

### После исправления

```
📄 Раздел_ПД№9_МКД-0109-2024-ПИР-ПБ_вер.01 (2).pdf
   KB: Раздел 9 (МЕС-БМК-04/24-ПБ)
   Шифр файла: МКД-0109-2024
   Шифр KB:    МЕС-БМК-04-24
   Совпадение: ❌
   SCORE: 0.85 ❌ Нет override ← ПРАВИЛЬНО!

📄 Раздел_ПД№9_МКД-0109-2024-ПИР-ПБ_вер.01 (2).pdf
   KB: Раздел 9 (МКД-0109-2024-ПИР-ПБ)
   Шифр файла: МКД-0109-2024
   Шифр KB:    МКД-0109-2024
   Совпадение: ✅
   SCORE: 0.99 ✅ KB Override ← ПРАВИЛЬНО!
```

---

## 📁 Изменённые файлы

1. **`v6/web_app_v6_cot_fallback.py`**
   - Строки 79-109: `_extract_code_from_filename()` - улучшено извлечение шифров
   - Строки 111-138: `_calculate_score()` - добавлена проверка шифра при boost по разделу

2. **`remove_kb_duplicates.py`** (новый файл)
   - Скрипт для удаления дубликатов из KB

3. **`knowledge_base.json`**
   - Удалено 13 дубликатов (61 → 48 записей)
   - Резервная копия: `knowledge_base_backup.json`

4. **`AGENTS_RULES/PROJECT_MEMORY.md`**
   - Добавлен раздел "Исправления v6 (09.04.2026)"

---

## 🎯 Рекомендации

### 1. Добавить недостающие эталоны в KB

**Проект МКД-0109-2024** (Зарайск):
- ❌ ОДИ (Раздел 11)
- ❌ ИУЛ (ИУЛ к ОДИ)
- ❌ ПЗ (Раздел 1)
- ❌ АР (Раздел 3)
- ❌ КР.РР (Раздел 4)
- ❌ ИОС5.3 (Раздел 5.5.3)
- ✅ ПБ (Раздел 9) - уже есть

**Проект МЕС-БМК-04/24** (Луховицы):
- ❌ ИОС1 (Подраздел 1)
- ❌ ИОС2 (Подраздел 2)
- ❌ ИОС4.1, ИОС4.2 (Подраздел 4)
- ❌ ИОС5 (Подраздел 5)
- ❌ ИОС6 (Подраздел 6)

### 2. Протестировать на реальных документах

Запустить сервер V6 и загрузить документы из папки "Анализ пакета 1":
```bash
cd /home/segun/CascadeProjects/Перед\ 0_2
python3 v6/web_app_v6_cot_fallback.py
# Адрес: http://localhost:5006
```

### 3. Проверить KB matching визуально

Открыть веб-интерфейс и проверить:
1. Badge статуса KB Override (✓/⚠/✗)
2. Score совпадения в %
3. Название найденной записи из KB
4. Шифр файла vs шифр KB

---

## 📅 Дата

2026-04-09 19:10

---

## 👤 Автор

Kilo (Cascade Project Assistant)
