#!/usr/bin/env python3
"""
ВАРИАНТ 3: Гибридный подход - объединение LLM и старых паттернов
- Сначала LLM (быстро, но может ошибаться)
- Затем валидация и дополнение через старые паттерны
- Финальная проверка качества
"""

import json
import re
from pathlib import Path
from typing import Dict, Any

# Импортируем robust JSON parser из варианта 2
exec(open("fix_v2_robust_json.py").read(), globals())

class HybridDocumentAnalyzer:
    """Гибридный анализатор: LLM + Паттерны + Валидация"""
    
    def __init__(self):
        self.api_url = "http://192.168.47.22:1234/v1/chat/completions"
        self.kb_data = self._load_kb()
        
    def _load_kb(self):
        """Загрузка Knowledge Base с fallback"""
        kb_paths = [
            Path("knowledge_base.json"),
            Path(__file__).parent.parent.parent.parent / "knowledge_base.json",
            Path("/home/segun/CascadeProjects/Перед 0_2/knowledge_base.json")
        ]
        for path in kb_paths:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"✅ Loaded {len(data)} KB entries from {path}")
                    return data
        return []
    
    def _validate_result(self, result: dict) -> dict:
        """Валидация и исправление результата"""
        issues = []
        
        # 1. Проверка на пустые ключи
        required_keys = ['title', 'customer', 'developer', 'year', 'document_type']
        for key in required_keys:
            if not result.get(key) or result[key] in ['—', 'неизвестно', '']:
                issues.append(f"Пустой ключ: {key}")
        
        # 2. Проверка year (должен содержать 4 цифры)
        if result.get('year'):
            year_match = re.search(r'20\d{2}', str(result['year']))
            if not year_match:
                issues.append("Некорректный год")
                result['year'] = None
        
        # 3. Проверка на галлюцинации (имена людей вместо организаций)
        for key in ['customer', 'developer']:
            if result.get(key):
                # Если содержит только ФИО (3 слова с заглавной буквы)
                if re.match(r'^[А-Я][а-я]+\s+[А-Я]\.[А-Я]\.$', result[key]):
                    issues.append(f"{key} содержит ФИО вместо организации")
                    result[key] = None
        
        # 4. Проверка content_summary (минимум 50 символов)
        if result.get('content_summary') and len(result['content_summary']) < 50:
            issues.append("Слишком короткое content_summary")
            result['content_summary'] = None
        
        if issues:
            print(f"⚠️ Проблемы валидации: {', '.join(issues)}")
        
        return result
    
    def _merge_results(self, llm_result: dict, pattern_result: dict) -> dict:
        """Объединение результатов LLM и паттернов"""
        merged = {}
        
        # Приоритет: LLM, если прошёл валидацию, иначе паттерны
        for key in ['title', 'customer', 'developer', 'year', 'document_type', 'content_summary', 'purpose']:
            llm_val = llm_result.get(key)
            pattern_val = pattern_result.get(key)
            
            # Если LLM дал валидное значение - берём его
            if llm_val and llm_val not in ['—', 'неизвестно', '']:
                merged[key] = llm_val
            # Иначе берём из паттернов
            elif pattern_val and pattern_val not in ['—', 'неизвестно', '']:
                merged[key] = pattern_val
            else:
                merged[key] = None
        
        return merged
    
    def analyze_document(self, filepath: Path, original_name: str = None) -> Dict[str, Any]:
        """
        Анализ документа с гибридным подходом:
        1. Извлечение текста
        2. LLM-анализ (быстро)
        3. Паттерн-анализ (надёжно)
        4. Валидация и объединение
        """
        filename = original_name or filepath.name
        result = {
            'filename': filename,
            'format': Path(filename).suffix[1:].upper(),
            'title': None,
            'customer': None,
            'developer': None,
            'year': None,
            'document_type': None,
            'content_summary': None,
            'purpose': None
        }
        
        # 1. Извлечение текста
        text = self._extract_text(filepath)
        if not text:
            result['error'] = 'Не удалось извлечь текст'
            return result
        
        # 2. LLM-анализ (если KB загружена)
        llm_result = {}
        if self.kb_data:
            try:
                llm_result = self._call_llm(text, filename)
                llm_result = self._validate_result(llm_result)
            except Exception as e:
                print(f"⚠️ LLM error: {e}")
        
        # 3. Паттерн-анализ (всегда)
        pattern_result = self._extract_with_patterns(text)
        
        # 4. Объединение результатов
        merged = self._merge_results(llm_result, pattern_result)
        result.update(merged)
        
        # 5. Финальная валидация
        result = self._validate_result(result)
        
        # 6. Статистика заполненности
        filled_keys = sum(1 for k in ['title', 'customer', 'developer', 'year', 'document_type', 'content_summary'] if result.get(k))
        result['_filled_keys'] = filled_keys
        result['_total_keys'] = 6
        
        return result
    
    def _extract_text(self, filepath: Path) -> str:
        """Извлечение текста из файла"""
        # (здесь должна быть логика извлечения из PDF/DOCX/XML)
        # Для примера возвращаем пустую строку
        return ""
    
    def _extract_with_patterns(self, text: str) -> dict:
        """Извлечение через старые паттерны (fallback)"""
        # (здесь должна быть логика из web_app_v4.py _extract_data)
        return {}
    
    def _call_llm(self, text: str, filename: str) -> dict:
        """Вызов LLM с улучшенным промптом"""
        import requests
        
        # Формируем промпт с акцентом на качество
        system_prompt = f"""Ты - эксперт по анализу проектной документации.

ЗАДАЧА: Извлечь 6 полей из текста документа.

КРИТИЧЕСКИ ВАЖНО:
1. Верни ТОЛЬКО JSON, без объяснений
2. Если поле не найдено - ставь null
3. ВСЕ значения на РУССКОМ языке

Поля:
- customer: Заказчик (организация после "Заказчик:")
- developer: Проектировщик (первая организация на титульном листе)
- title: Полное название документа
- year: Год (4 цифры, например "2025")
- document_type: Тип (Пояснительная записка, Раздел, ТУ, Выписка, Договор и т.д.)
- content_summary: Краткое содержание (2-3 предложения)

{self._get_examples(filename)}

ВЕРНИ JSON: {{"customer": "...", "developer": "...", "title": "...", "year": "...", "document_type": "...", "content_summary": "..."}}
"""
        
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:4000]}
            ],
            "temperature": 0.05,  # Ещё ниже для точности
            "max_tokens": 800
        }
        
        r = requests.post(self.api_url, json=payload, timeout=60)
        r.raise_for_status()
        resp = r.json()['choices'][0]['message']['content']
        
        # Используем robust parser
        return parse_json_robust(resp)
    
    def _get_examples(self, filename: str) -> str:
        """Получение примеров из KB"""
        if not self.kb_data:
            return ""
        
        # Semantic matching (как в варианте 1)
        # (упрощённо)
        return ""

# Применяем к web_app_v4.py
if __name__ == "__main__":
    print("📝 ВАРИАНТ 3: Гибридный подход")
    print("✅ Создан класс HybridDocumentAnalyzer")
    print("\n📊 Преимущества:")
    print("  - LLM для точности")
    print("  - Паттерны как fallback")
    print("  - Валидация качества")
    print("  - Статистика заполненности")
    print("\n🚀 Для применения:")
    print("  1. Интегрировать HybridDocumentAnalyzer в web_app_v4.py")
    print("  2. Или создать новый файл web_app_v6_hybrid.py")
