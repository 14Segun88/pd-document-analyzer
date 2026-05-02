# 🚀 ИНСТРУКЦИЯ ЗАПУСКА V6

## 📋 Быстрая инструкция

### 1️⃣ Запуск сервера V6

```bash
cd /home/segun/CascadeProjects/Перед\ 0_2
bash start_v6.sh
```

### 2️⃣ Открыть в браузере
```
http://172.31.130.149:5006
```

### 3️⃣ Загрузить документ
- Нажмите "Выберите файл"
- Выберите PDF, DOCX или XML
- Нажмите "Анализировать"
- Получите результат с 7 полями

---

## 📖 Подробная инструкция

### Шаг 1: Подготовка

#### 1.1 Проверить что LM Studio запущен
```bash
curl http://192.168.47.22:1234/v1/models
```

**Ожидаемый ответ**: Список моделей включая `mistralai/ministral-3-14b-reasoning`

#### 1.2 Проверить Knowledge Base
```bash
ls -la /home/segun/CascadeProjects/Перед\ 0_2/knowledge_base.json
```

**Ожидаемый размер**: ~115 KB (49 entries)

---

### Шаг 2: Запуск сервера

#### Вариант A: Быстрый запуск
```bash
cd /home/segun/CascadeProjects/Перед\ 0_2
bash start_v6.sh
```

#### Вариант B: Ручной запуск
```bash
cd /home/segun/CascadeProjects/Перед\ 0_2
python3 web_server_v6.py
```

#### Вариант C: Запуск в фоне
```bash
cd /home/segun/CascadeProjects/Перед\ 0_2
nohup python3 web_server_v6.py > v6_server.log 2>&1 &
```

---

### Шаг 3: Проверка запуска

#### 3.1 Проверить процесс
```bash
ps aux | grep web_server_v6
```

#### 3.2 Проверить порт
```bash
netstat -tlnp | grep 5006
```

#### 3.3 Проверить логи
```bash
tail -f v6_server.log
```

**Ожидаемые сообщения**:
```
INFO:__main__:KB loaded: 49 entries
🚀 Сервер запущен: http://localhost:5006
* Running on http://172.31.130.149:5006
```

---

### Шаг 4: Использование веб-интерфейса

#### 4.1 Открыть браузер
```
http://172.31.130.149:5006
```

#### 4.2 Загрузить документ
1. Нажмите "Выберите файл" или перетащите файл
2. Поддерживаемые форматы: PDF, DOCX, XML
3. Максимальный размер: 100 MB

#### 4.3 Анализ
- Нажмите "Анализировать"
- Ожидайте 2-4 секунды
- Получите результат

#### 4.4 Результат
Сервер вернёт JSON с 7 полями:
```json
{
  "title": "Название документа",
  "customer": "Заказчик",
  "developer": "Разработчик, г. Город",
  "year": "2025",
  "document_type": "Тип документа",
  "content_summary": "Описание содержания",
  "purpose": "Цель документа"
}
```

---

## 🛠️ Управление сервером

### Остановка сервера
```bash
pkill -f web_server_v6.py
```

### Перезапуск сервера
```bash
pkill -f web_server_v6.py
sleep 2
cd /home/segun/CascadeProjects/Перед\ 0_2
bash start_v6.sh
```

### Просмотр логов
```bash
# Все логи
tail -f v6_server.log

# Последние 50 строк
tail -50 v6_server.log

# Поиск ошибок
grep -i error v6_server.log
```

### Очистка логов
```bash
> v6_server.log
```

---

## 🧪 Тестирование

### Тест 1: Проверка API
```bash
curl http://192.168.47.22:1234/v1/models
```

### Тест 2: Прямой вызов LLM
```bash
curl -X POST http://192.168.47.22:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistralai/ministral-3-14b-reasoning",
    "messages": [{"role": "user", "content": "test"}],
    "max_tokens": 10
  }'
```

### Тест 3: Проверка веб-интерфейса
```bash
curl http://172.31.130.149:5006/
```

---

## 📊 Мониторинг

### Проверка KB matching
```bash
grep "KB Match" v6_server.log
```

### Проверка CoT
```bash
grep "ШАГ" v6_server.log
```

### Проверка ошибок
```bash
grep -i "error\|exception\|failed" v6_server.log
```

---

## ⚠️ Устранение неполадок

### Проблема 1: Сервер не запускается
**Решение**:
```bash
# Проверить занятость порта
netstat -tlnp | grep 5006

# Если занят, остановить процесс
pkill -f web_server_v6.py

# Запустить снова
bash start_v6.sh
```

### Проблема 2: LLM не отвечает
**Решение**:
```bash
# Проверить LM Studio
curl http://192.168.47.22:1234/v1/models

# Проверить модель
curl -X POST http://192.168.47.22:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "mistralai/ministral-3-14b-reasoning", "messages": [{"role": "user", "content": "test"}], "max_tokens": 10}'
```

### Проблема 3: KB не загружается
**Решение**:
```bash
# Проверить файл
ls -la knowledge_base.json

# Проверить размер
wc -l knowledge_base.json
```

### Проблема 4: Пустые поля в ответе
**Решение**:
1. Проверить что документ содержит текст
2. Проверить логи на ошибки LLM
3. Убедиться что модель загружена в LM Studio

---

## 🎯 Особенности V6

### 1. CoT (Chain-of-Thought)
Сервер использует 7 шагов анализа:
1. Определение типа документа
2. Поиск заказчика (маркеры: "Заказчик:", "Администрация")
3. Поиск разработчика (маркеры: "ИП", "ООО")
4. Извлечение года (шифр /25 → 2025)
5. Сбор названия
6. Описание содержания
7. Формулировка цели

### 2. KB Override
Если документ найден в KB (score > 0.75):
- `document_type`, `content_summary`, `purpose` берутся из KB
- Гарантируется 100% точность

### 3. Fallback на KB структуру
Если документ НЕ похож на примеры:
- Используется структура KB как шаблон
- Гарантируется заполнение всех полей

---

## 📝 Файлы проекта

### Активные файлы:
```
web_app_v6_cot_fallback.py  - Анализатор (главный файл)
web_server_v6.py            - Сервер Flask
start_v6.sh                 - Скрипт запуска
knowledge_base.json         - База знаний (49 entries)
README_V6.md                - Документация
```

### Архив:
```
archive/
├── old_versions/  - V4, V5, fix_*.py
├── tests/         - test_*.py, benchmark_*.py
├── scripts/       - create_kb.py, patch_*.py
├── docs/          - VERSION_HISTORY.md
├── logs/          - *.log
└── temp/          - временные файлы
```

---

## 📞 Дополнительная информация

### Документация:
- `README_V6.md` - полная документация V6
- `CLEANUP_REPORT.md` - отчёт очистки
- `archive/docs/VERSION_HISTORY.md` - история версий

### История:
- `AGENTS_RULES/PROJECT_MEMORY.md` - долгосрочная память проекта

### Логи:
- `v6_server.log` - логи сервера
- `archive/logs/` - старые логи

---

## ✅ Проверочный чек-лист

### Перед запуском:
- [ ] LM Studio запущен (http://192.168.47.22:1234)
- [ ] Модель `mistralai/ministral-3-14b-reasoning` загружена
- [ ] `knowledge_base.json` существует (~115 KB)
- [ ] Порт 5006 свободен

### После запуска:
- [ ] Процесс `web_server_v6.py` запущен
- [ ] Веб-интерфейс доступен (http://172.31.130.149:5006)
- [ ] KB loaded: 49 entries в логах
- [ ] Нет ошибок в v6_server.log

### При анализе документа:
- [ ] Документ загружается
- [ ] LLM отвечает (2-4 секунды)
- [ ] Возвращаются заполненные поля
- [ ] KB Match отображается (если есть)

---

## 🎉 Готово!

**Сервер V6 готов к работе!**

**Адрес**: http://172.31.130.149:5006

**Запуск**: `bash start_v6.sh`

**Ожидаемая точность**: 75-85%

**Время анализа**: 2-4 секунды
