#!/usr/bin/env python3
"""
ВАРИАНТ 2: Улучшенный JSON-парсинг с обработкой вложенных объектов
Исправляет критический баг с регулярным выражением
"""

import json
import re

def parse_json_robust(response_text: str) -> dict:
    """
    Надёжный парсер JSON из ответа LLM.
    Обрабатывает:
    - Markdown-обёртку ```json ... ```
    - Вложенные JSON-объекты
    - Мусор до/после JSON
    - Частичные ответы
    """
    
    # 1. Убираем markdown-обёртку
    text = response_text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
    
    # 2. Ищем первый JSON-объект
    # Используем подсчёт скобок для корректного захвата
    start_idx = text.find('{')
    if start_idx == -1:
        return {}
    
    brace_count = 0
    end_idx = start_idx
    
    for i, char in enumerate(text[start_idx:], start_idx):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i
                break
    
    if brace_count != 0:
        # Незакрытые скобки - пробуем добавить
        text = text[start_idx:] + '}' * brace_count
    else:
        text = text[start_idx:end_idx+1]
    
    # 3. Парсим JSON
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError as e:
        # 4. Пробуем исправить частые ошибки
        # Убираем trailing commas
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        # Экранируем переносы строк в значениях
        text = re.sub(r':\s*"([^"]*?)"', lambda m: ': "' + m.group(1).replace('\n', '\\n') + '"', text)
        
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except:
            pass
    
    return {}

# Тесты
if __name__ == "__main__":
    test_cases = [
        # Простой JSON
        ('{"customer": "ООО Тест", "title": "Документ"}', 
         {"customer": "ООО Тест", "title": "Документ"}),
        
        # JSON с markdown
        ('```json\n{"customer": "ООО Тест"}\n```', 
         {"customer": "ООО Тест"}),
        
        # JSON с мусором
        ('Вот результат: {"customer": "ООО Тест"} Спасибо!', 
         {"customer": "ООО Тест"}),
        
        # Вложенный JSON (не должно захватывать лишнее)
        ('{"outer": {"inner": "value"}, "other": "field"}', 
         {"outer": {"inner": "value"}, "other": "field"}),
        
        # Неправильный JSON (незакрытые скобки)
        ('{"customer": "ООО Тест"', 
         {}),
    ]
    
    print("🧪 Тестирование parse_json_robust:\n")
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = parse_json_robust(input_text)
        status = "✅" if result == expected else "❌"
        print(f"{status} Тест {i}:")
        print(f"   Вход: {input_text[:50]}...")
        print(f"   Результат: {result}")
        print(f"   Ожидалось: {expected}\n")
