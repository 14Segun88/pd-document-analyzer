#!/usr/bin/env python3
"""
ВАРИАНТ 1: Простое исправление - добавление LLM-вызовов
Базируется на текущей версии web_app_v4.py
"""

import re

# Читаем текущий файл
with open("web_app_v4.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Добавляем импорты
if "import base64" not in content:
    content = content.replace(
        "import json",
        "import json\nimport base64\nimport requests"
    )

# 2. Добавляем __init__ с KB
init_method = '''
    def __init__(self):
        self.api_url = "http://192.168.47.22:1234/v1/chat/completions"
        self.kb_data = []
        try:
            kb_path = Path(__file__).parent.parent.parent.parent / "knowledge_base.json"
            if not kb_path.exists():
                kb_path = Path("knowledge_base.json")
            if kb_path.exists():
                with open(kb_path, "r", encoding="utf-8") as f:
                    self.kb_data = json.load(f)
                logger.info(f"Loaded {len(self.kb_data)} KB entries")
        except Exception as e:
            logger.warning(f"Knowledge Base not loaded: {e}")
'''

if "def __init__(self):" not in content:
    # Вставляем после class DocumentAnalyzer:
    content = content.replace(
        'class DocumentAnalyzer:\n    """Анализатор документации с точными паттернами."""',
        f'class DocumentAnalyzer:\n    """Анализатор документации с LLM + KB."""{init_method}'
    )

# 3. Добавляем вспомогательные методы перед analyze_pdf
helper_methods = '''
    def _get_semantic_examples(self, filename: str) -> str:
        """Подбирает до 3 примеров из KB по имени файла."""
        if not self.kb_data:
            return ""
        
        def tokenize(text):
            return set(re.findall(r'[а-яА-Яa-zA-Z0-9]+', text.lower()))
        
        file_tokens = tokenize(filename)
        scored = []
        for entry in self.kb_data:
            src = entry.get('_source_doc', '')
            title = entry.get('title', '')
            entry_tokens = tokenize(src + " " + title)
            score = len(file_tokens.intersection(entry_tokens))
            if score > 0:
                scored.append((score, entry))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        top_3 = [e[1] for e in scored[:3]]
        
        if not top_3:
            return ""
        
        examples = "\\nПРИМЕРЫ ИЗ БАЗЫ ЗНАНИЙ:\\n"
        for i, ex in enumerate(top_3):
            clean = {k: v for k, v in ex.items() if not k.startswith('_')}
            examples += f"\\nПРИМЕР {i+1}:\\n{json.dumps(clean, ensure_ascii=False, indent=2)}\\n"
        return examples

    def _call_llm(self, text: str, filename: str) -> dict:
        """Вызов Mistral 14B Reasoning для извлечения полей."""
        system_prompt = f"""Ты - анализатор проектной документации. Извлеки 6 полей из текста.

ПРАВИЛА:
1. customer (Заказчик) - ищи после слова "Заказчик" или "СОГЛАСОВАНО"
2. developer (Проектировщик) - первая организация на титульном листе
3. title (Название) - полное наименование документа
4. year (Год) - год составления или из шифра (напр. /25 = 2025)
5. document_type (Тип) - категория: Пояснительная записка, Раздел, ТУ, Выписка ЕГРН и т.д.
6. content_summary (Содержимое) - краткое описание 2-3 предложения

ВЕРНИ СТРОГО JSON:
{{"customer": "...", "developer": "...", "title": "...", "year": "...", "document_type": "...", "content_summary": "..."}}

ВСЕ ЗНАЧЕНИЯ НА РУССКОМ. Без markdown-обёртки.
{self._get_semantic_examples(filename)}
"""
        
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:4000]}
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        try:
            r = requests.post(self.api_url, json=payload, timeout=60)
            r.raise_for_status()
            resp = r.json()['choices'][0]['message']['content']
            
            # Очистка от markdown
            resp = re.sub(r'```json\\s*', '', resp)
            resp = re.sub(r'```\\s*$', '', resp)
            resp = resp.strip()
            
            # Парсинг JSON
            if resp.startswith('{'):
                return json.loads(resp)
            
            # Поиск JSON в тексте
            match = re.search(r'\\{[^{}]*\\}', resp, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            
            logger.error(f"No JSON in response: {resp[:200]}")
            return {}
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return {}

    def _call_olmocr(self, img_bytes: bytes) -> str:
        """OCR через OLMOCR 7B для сканов."""
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        payload = {
            "model": "local-model",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Извлеки весь текст с изображения в формате markdown."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        try:
            r = requests.post(self.api_url, json=payload, timeout=120)
            if r.status_code == 400:
                raise Exception("olmocr error")
            r.raise_for_status()
            return r.json()['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"OLMOCR error: {e}")
            raise Exception("olmocr error")

'''

if "_get_semantic_examples" not in content:
    # Вставляем перед первым методом analyze
    content = content.replace(
        "    def analyze_pdf",
        helper_methods + "    def analyze_pdf"
    )

# 4. Модифицируем analyze_pdf для использования LLM
old_analyze_pdf = '''    def analyze_pdf(self, filepath: Path, original_name: str = None) -> Dict[str, Any]:
        """Анализ PDF файла."""
        result = self._init_result(original_name or filepath.name, 'PDF')

        if not HAS_PYMUPDF:
            return {'error': 'PyMuPDF не установлен', 'filename': original_name or filepath.name}

        try:
            doc = fitz.open(filepath)
            text_content = ""

            for page_num, page in enumerate(doc):
                text = page.get_text()
                if len(text.strip()) < 100 and HAS_TESSERACT:
                    try:
                        pix = page.get_pixmap()
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        text = pytesseract.image_to_string(img, lang='rus+eng')
                    except Exception:
                        pass
                text_content += text + "\\n"

            doc.close()
            result['raw_text'] = text_content[:20000]

            self._extract_data(text_content, result)

        except Exception as e:
            result['error'] = str(e)

        return result'''

new_analyze_pdf = '''    def analyze_pdf(self, filepath: Path, original_name: str = None) -> Dict[str, Any]:
        """Анализ PDF файла с LLM."""
        result = self._init_result(original_name or filepath.name, 'PDF')

        if not HAS_PYMUPDF:
            return {'error': 'PyMuPDF не установлен', 'filename': original_name or filepath.name}

        try:
            doc = fitz.open(filepath)
            text_content = ""

            for page_num, page in enumerate(doc):
                text = page.get_text()
                text_content += text + "\\n"
                if len(text_content) > 4000:
                    break

            # Проверка на скан (мало полезного текста)
            clean_text = re.sub(r'[^а-яА-Яa-zA-Z0-9]', '', text_content)
            if len(clean_text) < 150:
                result['format'] = 'PDF [SCAN] (OLMOCR)'
                try:
                    pix = doc[0].get_pixmap()
                    img_bytes = pix.tobytes("jpeg")
                    text_content = self._call_olmocr(img_bytes)
                except Exception as e:
                    if "olmocr error" in str(e):
                        result['error'] = "olmocr error"
                        return result
                    # Fallback на Tesseract
                    if HAS_TESSERACT:
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        text_content = pytesseract.image_to_string(img, lang='rus+eng')

            doc.close()
            
            # Сначала пробуем LLM
            if len(self.kb_data) > 0:
                llm_data = self._call_llm(text_content, result['filename'])
                if llm_data and len(llm_data) >= 3:
                    result.update({k: v for k, v in llm_data.items() if k in result})
                    return result
            
            # Fallback на старые паттерны
            result['raw_text'] = text_content[:20000]
            self._extract_data(text_content, result)

        except Exception as e:
            result['error'] = str(e)

        return result'''

content = content.replace(old_analyze_pdf, new_analyze_pdf)

# Сохраняем
with open("web_app_v5_llm.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Создан web_app_v5_llm.py с LLM-интеграцией")
print("📝 Для применения: cp web_app_v5_llm.py web_app_v4.py")
