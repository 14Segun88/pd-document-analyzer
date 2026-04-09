import re

with open(".kilo/worktrees/playful-flower/web_app_v4.py", "r", encoding="utf-8") as f:
    text = f.read()

prefix = text.split("class DocumentAnalyzer:")[0]
suffix = "\n\n# HTML шаблон - простая форма без внешних библиотек\nHTML_TEMPLATE =" + text.split("# HTML шаблон - простая форма без внешних библиотек\nHTML_TEMPLATE =")[1]

imports_addition = """import base64
import requests

"""

if "import base64" not in prefix:
    prefix = prefix.replace("import json", "import json\nimport base64\nimport requests")


new_class = '''class DocumentAnalyzer:
    """Анализатор документации с интеграцией Knowledge Base, Mistral 14B Reasoning и OLMOCR."""
    
    def __init__(self):
        self.api_url = "http://192.168.47.22:1234/v1/chat/completions"
        self.kb_data = []
        try:
            with open("knowledge_base.json", "r", encoding="utf-8") as f:
                self.kb_data = json.load(f)
        except Exception as e:
            logger.error(f"Не удалось загрузить Knowledge Base: {e}")

    def _get_semantic_examples(self, filename: str) -> str:
        """Подбирает до 3 лучших примеров на основе имени файла (Semantic Matching)."""
        if not self.kb_data:
            return ""
        
        def tokenize(text):
            return set(re.findall(r'[а-яА-Яa-zA-Z0-9]+', text.lower()))
            
        file_tokens = tokenize(filename)
        
        scored_entries = []
        for entry in self.kb_data:
            src_name = entry.get('_source_doc', '')
            title = entry.get('title', '')
            entry_tokens = tokenize(src_name + " " + title)
            
            score = len(file_tokens.intersection(entry_tokens))
            scored_entries.append((score, entry))
        
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        top_3 = [e[1] for e in scored_entries[:3]]
        
        examples_str = "ПРИМЕРЫ ЖЕЛАЕМЫХ ОТВЕТОВ:\\n\\n"
        for i, ex in enumerate(top_3):
            # Убираем внутренние системные поля (_source_doc и т.п.)
            clean_ex = {k: v for k, v in ex.items() if not k.startswith('_')}
            examples_str += f"ПРИМЕР {i+1}:\\n```json\\n{json.dumps(clean_ex, ensure_ascii=False, indent=2)}\\n```\\n\\n"
        return examples_str

    def _call_olmocr(self, img_bytes: bytes) -> str:
        """Отправляет изображение в OLMOCR 7B для извлечения текста."""
        base64_image = base64.b64encode(img_bytes).decode('utf-8')
        payload = {
            "model": "local-model",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this image and output as formatting markdown text with tables and structures."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        try:
            r = requests.post(self.api_url, json=payload, timeout=120)
            if r.status_code == 400:
                raise Exception("olmocr error")
            r.raise_for_status()
            return r.json()['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            if getattr(e.response, "status_code", None) == 400:
                raise Exception("olmocr error")
            logger.error(f"OLMOCR API Error: {e}")
            raise Exception("olmocr error")

    def _extract_with_llm(self, text: str, filename: str) -> dict:
        """Обработка текста через Mistral 14B Reasoning с COT и строгим JSON."""
        system_prompt = f"""ВЫ - ПРОФЕССИОНАЛЬНЫЙ АНАЛИЗАТОР ПРОЕКТНОЙ СТРОИТЕЛЬНОЙ ДОКУМЕНТАЦИИ.
Ваша цель: извлечь 6 ключевых полей из переданного текста.

Schema Definitions (ЖЕЛЕЗНАЯ ЛОГИКА):
1. Заказчик: Ищите в ТЗ/ЗнП или на титульном листе СТРОГО ПОСЛЕ проектировщика. Маркер — слово «Заказчик».
2. Проектировщик (developer): Идет самым первым (верхним) на титульном листе. (В XML это ProjectDocumentationAuthors).
3. Названия организаций: Берите полные или краткие названия компаний из ТЗ. ОГРН или ИНН НЕ ТРЕБУЕТСЯ.
4. Название документа (title): Строго полное наименование по ТЗ без самовольного объединения переносов строк.

ПРАВИЛО ФОРМАТИРОВАНИЯ (Chain of Thought + JSON):
Вы имеете право писать любые размышления в тегах <think></think>. В конце ВЫ ОБЯЗАНЫ вернуть строго валидный JSON блок.
Принудительно генерируйте поля *_reasoning для цепочки мыслей в самом JSON перед выдачей финализированного поля.

ПРИМЕР ВАШЕГО JSON ФОРМАТА:
```json
{{
  "Customer_reasoning": "Я вижу слово 'Заказчик' рядом с ООО Ромашка",
  "customer": "ООО Ромашка",
  "Developer_reasoning": "Первым на листе идет текст 'Проектное бюро...'",
  "developer": "ООО Проектное бюро",
  "title": "Раздел ПД...",
  "year": "2024 г.",
  "document_type": "Текстовая часть...",
  "content_summary": "Описание...",
  "purpose": "Обоснование..."
}}
```
ВСЕ ЗНАЧЕНИЯ в JSON должны быть СТРОГО НА РУССКОМ ЯЗЫКЕ. Никакого перевода ключей кроме базовых (title, customer, developer, year, document_type, content_summary, purpose)!

{self._get_semantic_examples(filename)}
"""

        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.1,
            "max_tokens": 3000
        }
        
        try:
            r = requests.post(self.api_url, json=payload, timeout=300)
            r.raise_for_status()
            resp_text = r.json()['choices'][0]['message']['content']
            
            # Убираем <think>...</think> если модель его вывела вне json
            clean_text = re.sub(r'<think>.*?</think>', '', resp_text, flags=re.DOTALL)
            
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', clean_text, re.DOTALL | re.IGNORECASE)
            if not json_match:
                json_match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
                
            if json_match:
                parsed = json.loads(json_match.group(1))
                return parsed
            else:
                logger.error("JSON cutoff или нет JSON в ответе Mistral.")
                return {}
        except Exception as e:
            logger.error(f"LLM API Error: {e}")
            return {}

    def _init_result(self, filename: str, format_type: str) -> dict:
        return {
            'filename': filename,
            'format': format_type,
            'title': None,
            'customer': None,
            'developer': None,
            'year': None,
            'document_type': None,
            'content_summary': None,
            'purpose': None,
            'raw_text': None,
        }

    def analyze_pdf(self, filepath, original_name: str = None) -> dict:
        filename = original_name or filepath.name
        result = self._init_result(filename, 'PDF')
        
        if not HAS_PYMUPDF:
            return {'error': 'PyMuPDF не установлен', 'filename': filename}
            
        text_limit = 4000 if len(self.kb_data) > 0 else 15000
        
        try:
            doc = fitz.open(filepath)
            text_content = ""
            # Читаем страницы, пока не наберём лимит
            for page in doc:
                text_content += page.get_text() + "\\n"
                if len(text_content) > text_limit:
                    break
                    
            clean_text = re.sub(r'[^а-яА-Яa-zA-Z0-9]', '', text_content)
            
            # Если текста мало, предполагаем что это СКАН
            if len(clean_text) < 150:
                result['format'] = 'PDF [SCAN] (Processed by olmocr)'
                try:
                    pix = doc[0].get_pixmap()
                    img_bytes = pix.tobytes("jpeg")
                    text_content = self._call_olmocr(img_bytes)
                except Exception as e:
                    if str(e) == "olmocr error":
                        raise Exception("olmocr error")
                    else:
                        logger.error(f"Fallback to PyTesseract due to OLMOCR fail: {e}")
                        if HAS_TESSERACT:
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            text_content = pytesseract.image_to_string(img, lang='rus+eng')

            result['raw_text'] = text_content[:text_limit]
            
            llm_data = self._extract_with_llm(result['raw_text'], result['filename'])
            result.update({k: v for k, v in llm_data.items() if k in result})
            
        except Exception as e:
            if "olmocr error" in str(e):
                result['error'] = "olmocr error"
            else:
                result['error'] = str(e)
        
        return result
    
    def analyze_docx(self, filepath, original_name: str = None) -> dict:
        filename = original_name or filepath.name
        result = self._init_result(filename, 'DOCX')
        
        if not HAS_PYTHON_DOCX:
            return {'error': 'python-docx не установлен', 'filename': filename}
            
        text_limit = 4000 if len(self.kb_data) > 0 else 15000
        
        try:
            doc = Document(filepath)
            text_content = "\\n".join(para.text for para in doc.paragraphs)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text_content += " " + cell.text
            result['raw_text'] = text_content[:text_limit]
            
            llm_data = self._extract_with_llm(result['raw_text'], result['filename'])
            result.update({k: v for k, v in llm_data.items() if k in result})
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def analyze_xml(self, filepath, original_name: str = None) -> dict:
        import xml.etree.ElementTree as ET
        filename = original_name or filepath.name
        result = self._init_result(filename, 'XML')
        
        text_limit = 4000 if len(self.kb_data) > 0 else 15000
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            text_content = ' '.join(t.text for t in root.iter() if t.text)
            result['raw_text'] = text_content[:text_limit]
            
            llm_data = self._extract_with_llm(result['raw_text'], result['filename'])
            result.update({k: v for k, v in llm_data.items() if k in result})
        except Exception as e:
            result['error'] = str(e)
            
        return result
'''

final_text = prefix + new_class + suffix

with open(".kilo/worktrees/playful-flower/web_app_v4.py", "w", encoding="utf-8") as f:
    f.write(final_text)

print("Patch applied.")
