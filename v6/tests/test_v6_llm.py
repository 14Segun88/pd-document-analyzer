#!/usr/bin/env python3
"""Тест V6 сервера с реальным документом"""

import requests
import json

# Тестовый документ (простой текст)
test_text = """
ПОЯСНИТЕЛЬНАЯ ЗАПИСКА
Шифр: 157/25-ПЗ

Заказчик: ГКУ МО «Дирекция заказчика капитального строительства»
Проектировщик: ООО «Мосрегионпроект», г. Электросталь
Год: 2025

Раздел содержит описание архитектурных решений для школы на 1100 мест.
Общая площадь здания 15420 м².
"""

# Отправляем запрос на V6
url = "http://localhost:5006/analyze"

# Пробуем через API
print("🧪 Тестирование V6 сервера...")
print(f"URL: {url}")
print()

# Вариант 1: через requests
try:
    # Создаём временный файл
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_text)
        temp_file = f.name

    # Отправляем файл
    with open(temp_file, 'rb') as f:
        files = {'file': ('test_document.txt', f, 'text/plain')}
        response = requests.post(url, files=files)

    os.unlink(temp_file)

    if response.status_code == 200:
        result = response.json()
        print("✅ Ответ получен!")
        print()
        print("📊 Результат:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print()

        # Проверяем заполненность
        filled = sum(1 for k in ['title', 'customer', 'developer', 'year', 'document_type', 'content_summary'] if result.get(k))
        total = 6
        print(f"📈 Заполненность: {filled}/{total} ({filled/total*100:.0f}%)")

        if filled >= 4:
            print("✅ LLM работает корректно!")
        else:
            print("⚠️ LLM вернул мало данных. Проверьте логи.")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Исключение: {e}")

print()
print("=" * 60)
print()

# Вариант 2: Прямой вызов LLM API
print("🔬 Прямой тест LLM API (Mistral 14B Reasoning)...")

llm_url = "http://192.168.47.22:1234/v1/chat/completions"
llm_payload = {
    "model": "mistralai/ministral-3-14b-reasoning",
    "messages": [
        {
            "role": "system",
            "content": "Ты — анализатор документов. Извлеки данные и верни JSON с полями: title, customer, developer, year."
        },
        {
            "role": "user",
            "content": test_text
        }
    ],
    "max_tokens": 500,
    "temperature": 0.1
}

try:
    response = requests.post(llm_url, json=llm_payload, timeout=30)
    if response.status_code == 200:
        llm_result = response.json()
        content = llm_result['choices'][0]['message'].get('content', '')
        reasoning = llm_result['choices'][0]['message'].get('reasoning_content', '')

        print("✅ LLM API работает!")
        print()
        print(f"📝 Reasoning: {reasoning[:200]}..." if reasoning else "📝 Reasoning: отсутствует")
        print()
        print(f"📄 Content: {content[:300]}...")

        if reasoning:
            print()
            print("✅ CoT Reasoning активен!")
        else:
            print()
            print("⚠️ CoT Reasoning не активен (проверьте модель)")
    else:
        print(f"❌ LLM API ошибка: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"❌ LLM API исключение: {e}")
