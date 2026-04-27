#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import json
import logging
import tempfile
import requests
import defusedxml.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, IO
from datetime import datetime
from difflib import SequenceMatcher
from flask import Flask, request, render_template_string, jsonify
from werkzeug.utils import secure_filename

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from docx import Document
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False

COT_SYSTEM_PROMPT = """Ты — эксперт по анализу проектной документации.

ПРИМЕРЫ ИЗ БАЗЫ ЗНАНИЙ:
{kb_examples}

ЗАДАЧА: Извлеки из документа 7 полей в JSON формате.

ПРАВИЛА:
- title: полное название документа с шифром (например: "Раздел 3 АР (157/25-АР)")
- customer: заказчик (например: "ГКУ МО «ДЗКС»")
- developer: разработчик с городом (например: "ООО «Мосрегионпроект», г. Электросталь")
- year: год (из шифра /25 → 2025)
- document_type: тип (например: "Проектная документация", "Результаты ИГДИ")
- content_summary: краткое содержание (3-4 ключевых пункта)
- purpose: цель документа (для чего он нужен)

ИСПОЛЬЗУЙ ПРЕДОСТАВЛЕННУЮ НИЖЕ СТРУКТУРУ XML КАК ПОДСКАЗКУ (XML Structure Hints).

ВАЖНО: Если документ похож на один из примеров, используй его структуру.
Если документ новый — проанализируй его самостоятельно, следуя 7 шагам CoT.

ПРОЦЕСС (Chain-of-Thought):
ШАГ 1: ОПРЕДЕЛИ ТИП ДОКУМЕНТА
ШАГ 2: НАЙДИ ЗАКАЗЧИКА (маркеры: "Заказчик:", "Администрация")
ШАГ 3: НАЙДИ РАЗРАБОТЧИКА (маркеры: "ИП", "ООО")
ШАГ 4: ИЗВЛЕКИ ГОД (шифр /25 → 2025)
ШАГ 5: СОБЕРИ НАЗВАНИЕ
ШАГ 6: ОПИШИ СОДЕРЖАНИЕ
ШАГ 7: СФОРМУЛИРУЙ ЦЕЛЬ

ОТВЕТЬ ТОЛЬКО В JSON ФОРМАТЕ.

Твой ответ должен начинаться с <reasoning> где ты опишешь все 7 шагов анализа, и заканчиваться JSON объектом в блоке ```json."""

class DocumentAnalyzer:
    def __init__(self):
        self.kb_data = []
        self._load_kb()

    def _load_kb(self):
        kb_path = Path(__file__).parent.parent / "knowledge_base.json"
        if kb_path.exists():
            try:
                with open(kb_path, 'r', encoding='utf-8') as f:
                    self.kb_data = json.load(f)
                logger.info(f"KB loaded: {len(self.kb_data)} entries from {kb_path.absolute()}")
            except Exception as e:
                logger.warning(f"KB not loaded: {e}")

    def _extract_code_from_filename(self, filename):
        # Improved regex to handle both / and - or _ in codes

        # Specific match for the common pattern in KB: МЕС-БМК-04/24
        match = re.search(r'([А-ЯA-Z]{2,4}-[А-ЯA-Z]{2,4}-\d{2,4}/\d{2,4})', filename)
        if match:
            return match.group(1)

        # Matches formats like 157/25, 157-25, 157_25
        match = re.search(r'(\d{2,4}[/_]\d{2,4})', filename)
        if match:
            return match.group(1).replace('_', '/')

        # Matches formats like АР-2024-0424
        # Supporting Cyrillic and Latin
        match = re.search(r'([А-ЯA-Z]{2,4}-\d{2,4}-\d{3,4})', filename)
        if match:
            return match.group(1)

        return None

    def _calculate_score(self, filename, kb_title):
        score = SequenceMatcher(None, filename.lower(), kb_title.lower()).ratio()

        file_section = re.search(r'ПД№(\d+)', filename)
        kb_section = re.search(r'Раздел\s*(\d+)', kb_title)
        if file_section and kb_section and file_section.group(1) == kb_section.group(1):
            score = max(score, 0.99)

        file_code = self._extract_code_from_filename(filename)
        kb_code = self._extract_code_from_filename(kb_title)
        if file_code and kb_code and file_code == kb_code:
            score = max(score, 0.85)

        return score

    def _get_kb_matching_entries(self, filename, top_n=3):
        scored_entries = []
        for entry in self.kb_data:
            kb_title = entry.get('title', '')
            score = self._calculate_score(filename, kb_title)
            scored_entries.append((score, entry))

        scored_entries.sort(key=lambda x: x[0], reverse=True)
        return [(score, entry) for score, entry in scored_entries[:top_n]]

    def _get_kb_direct_fields(self, filename):
        matches = self._get_kb_matching_entries(filename, top_n=1)
        if matches and matches[0][0] >= 0.75:
            entry = matches[0][1]
            return {
                'document_type': entry.get('document_type'),
                'content_summary': entry.get('content_summary'),
                'purpose': entry.get('purpose'),
                'kb_match': True,
                'kb_title': entry.get('title'),
                'kb_score': round(matches[0][0] * 100)
            }
        return {}

    def _get_semantic_examples_enhanced(self, filename: str, doc_text: str) -> str:
        matches = self._get_kb_matching_entries(filename, top_n=3)

        examples = []
        for i, (score, entry) in enumerate(matches):
            example = f"ПРИМЕР {i+1} (Схожесть: {round(score*100)}%):\n"
            example += f"Название: {entry.get('title')}\n"
            example += f"Заказчик: {entry.get('customer')}\n"
            example += f"Разработчик: {entry.get('developer')}\n"
            example += f"Тип: {entry.get('document_type')}\n"
            example += f"Суть: {entry.get('content_summary')}\n"
            example += f"Цель: {entry.get('purpose')}\n"
            examples.append(example)

        return "\n\n".join(examples)

    def _call_llm(self, text, filename):
        url = "http://192.168.47.22:1234/v1/chat/completions"

        kb_examples = self._get_semantic_examples_enhanced(filename, text[:2000])

        payload = {
            "model": "mistralai/ministral-3-14b-reasoning",
            "messages": [
                {"role": "system", "content": COT_SYSTEM_PROMPT.format(kb_examples=kb_examples)},
                {"role": "user", "content": f"ФАЙЛ: {filename}\n\nТЕКСТ ДОКУМЕНТА:\n{text[:4000]}"}
            ],
            "temperature": 0.1,
            "max_tokens": 3000,
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            result = response.json()
            content = result['choices'][0]['message']['content']

            # Попытка извлечь CoT reasoning если есть (native or manual)
            reasoning = result['choices'][0]['message'].get('reasoning_content', "")

            # Manual extraction if prompt instructed to use <reasoning>
            if not reasoning and "<reasoning>" in content:
                match = re.search(r'<reasoning>(.*?)</reasoning>', content, re.DOTALL)
                if match:
                    reasoning = match.group(1).strip()

            if reasoning:
                logger.info(f"CoT Reasoning found for {filename}: {reasoning[:100]}...")

            # Extract JSON from code block if present
            if "```json" in content:
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))

            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM Error for {filename}: {e}")
            # Fallback на пустую структуру
            return {
                "title": filename,
                "customer": "Error",
                "developer": "Error",
                "year": "Error",
                "document_type": "Error",
                "content_summary": str(e),
                "purpose": "Error"
            }

    def _init_result(self, filename: str, format_type: str) -> Dict[str, Any]:
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

    def analyze_pdf(self, filepath: Path, original_name: Optional[str] = None) -> Dict[str, Any]:
        filename = original_name or filepath.name
        res = self._init_result(filename, 'pdf')

        if not HAS_PYMUPDF:
            res['content_summary'] = "Error: PyMuPDF not installed"
            return res

        try:
            text = ""
            with fitz.open(str(filepath)) as doc:
                # Берем первые 5 страниц для анализа
                for page in doc[:5]:
                    text += page.get_text()

            res['raw_text'] = text
            llm_res = self._call_llm(text, filename)
            res.update(llm_res)

            # KB Override
            kb_fields = self._get_kb_direct_fields(filename)
            if kb_fields:
                res.update(kb_fields)

            return res
        except Exception as e:
            res['content_summary'] = f"Error: {e}"
            return res

    def analyze_docx(self, filepath: Path, original_name: Optional[str] = None) -> Dict[str, Any]:
        filename = original_name or filepath.name
        res = self._init_result(filename, 'docx')

        if not HAS_PYTHON_DOCX:
            res['content_summary'] = "Error: python-docx not installed"
            return res

        try:
            doc = Document(str(filepath))
            text = "\n".join([p.text for p in doc.paragraphs[:100]])

            res['raw_text'] = text
            llm_res = self._call_llm(text, filename)
            res.update(llm_res)

            # KB Override
            kb_fields = self._get_kb_direct_fields(filename)
            if kb_fields:
                res.update(kb_fields)

            return res
        except Exception as e:
            res['content_summary'] = f"Error: {e}"
            return res

    def analyze_xml(self, filepath: Path, original_name: Optional[str] = None) -> Dict[str, Any]:
        filename = original_name or filepath.name
        res = self._init_result(filename, 'xml')

        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            # Дамп структуры XML для LLM
            xml_structure = ""
            for child in list(root)[:20]:
                xml_structure += f"<{child.tag}> {str(child.text)[:50]}\n"

            res['raw_text'] = xml_structure
            llm_res = self._call_llm(xml_structure, filename)
            res.update(llm_res)

            # KB Override
            kb_fields = self._get_kb_direct_fields(filename)
            if kb_fields:
                res.update(kb_fields)

            return res
        except Exception as e:
            res['content_summary'] = f"Error: {e}"
            return res

def generate_md_report(results: List[Dict], output_dir: Path) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_v6_{timestamp}.md"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Отчёт об анализе документов (Версия V6)\n")
        f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n")

        for i, res in enumerate(results):
            f.write(f"## {i+1}. {res.get('filename')}\n")
            if res.get('kb_match'):
                f.write(f"> **✓ Совпадение с Базой Знаний ({res.get('kb_score')}%):** {res.get('kb_title')}\n\n")

            f.write(f"| Поле | Значение |\n")
            f.write(f"| :--- | :--- |\n")
            f.write(f"| **Название** | {res.get('title')} |\n")
            f.write(f"| **Заказчик** | {res.get('customer')} |\n")
            f.write(f"| **Разработчик** | {res.get('developer')} |\n")
            f.write(f"| **Год** | {res.get('year')} |\n")
            f.write(f"| **Тип** | {res.get('document_type')} |\n")
            f.write(f"| **Содержание** | {res.get('content_summary')} |\n")
            f.write(f"| **Цель** | {res.get('purpose')} |\n\n")

    return str(filepath)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

analyzer = DocumentAnalyzer()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>v6 CoT Analyzer - Множественная загрузка</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; padding: 20px; color: #fff; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; font-size: 2em; }
        .version-badge { background: #e94560; padding: 5px 15px; border-radius: 20px; font-size: 0.8em; margin-left: 10px; }
        .upload-zone { background: rgba(255,255,255,0.1); border-radius: 20px; padding: 40px; text-align: center; margin-bottom: 30px; backdrop-filter: blur(10px); }
        .file-input { display: none; }
        .upload-btn { background: #e94560; color: white; padding: 15px 40px; border-radius: 30px; cursor: pointer; display: inline-block; transition: 0.3s; font-weight: bold; }
        .upload-btn:hover { background: #ff4d6d; transform: scale(1.05); }
        .results { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; margin-top: 30px; }
        .card { background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; border: 1px solid rgba(255,255,255,0.1); transition: 0.3s; position: relative; }
        .card:hover { transform: translateY(-5px); background: rgba(255,255,255,0.08); }
        .card.kb-match { border-left: 5px solid #00d2ff; }
        .kb-badge { position: absolute; top: 10px; right: 10px; background: #00d2ff; font-size: 0.7em; padding: 2px 8px; border-radius: 10px; color: #000; font-weight: bold; }
        .card h3 { color: #e94560; margin-bottom: 15px; font-size: 1.1em; word-break: break-all; }
        .field { margin-bottom: 10px; font-size: 0.9em; }
        .field-label { color: #888; font-weight: bold; display: block; margin-bottom: 2px; }
        .field-value { color: #eee; }
        #loading { display: none; margin-top: 20px; text-align: center; }
        .spinner { border: 4px solid rgba(255,255,255,0.1); border-left: 4px solid #e94560; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .md-btn { background: #4ecca3; margin-top: 20px; padding: 10px 20px; border-radius: 5px; color: #fff; text-decoration: none; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📑 Document Analyzer <span class="version-badge">v6 CoT</span></h1>

        <div class="upload-zone">
            <h3>Загрузите до 10 документов</h3>
            <p style="margin: 15px 0; color: #888;">Поддерживаются PDF, DOCX, XML</p>
            <label class="upload-btn">
                <input type="file" class="file-input" multiple accept=".pdf,.docx,.xml" onchange="uploadFiles(this.files)">
                Выберите файлы
            </label>
        </div>

        <div id="loading">
            <div class="spinner"></div>
            <p>Анализируем документы... (2-4 сек на файл)</p>
        </div>

        <div id="resultsContainer" style="display: none;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h2>Результаты анализа</h2>
                <button onclick="downloadReport()" class="md-btn">💾 Скачать MD Отчёт</button>
            </div>
            <div class="results" id="resultsGrid"></div>
        </div>
    </div>

    <script>
        let lastResults = [];

        async function uploadFiles(files) {
            if (files.length === 0) return;
            if (files.length > 10) {
                alert("Максимум 10 файлов за один раз");
                return;
            }

            const loading = document.getElementById('loading');
            const container = document.getElementById('resultsContainer');
            const grid = document.getElementById('resultsGrid');
            
            loading.style.display = 'block';
            container.style.display = 'none';
            grid.innerHTML = '';
            lastResults = [];

            for (let file of files) {
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch('/analyze', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    lastResults.push(data);
                    renderCard(data);
                } catch (e) {
                    console.error(e);
                }
            }

            loading.style.display = 'none';
            container.style.display = 'block';
        }

        function renderCard(data) {
            const grid = document.getElementById('resultsGrid');
            const card = document.createElement('div');
            card.className = `card ${data.kb_match ? 'kb-match' : ''}`;
            
            if (data.kb_match) {
                const badge = document.createElement('div');
                badge.className = 'kb-badge';
                badge.textContent = `✓ KB ${data.kb_score}%`;
                card.appendChild(badge);
            }
            
            const title = document.createElement('h3');
            title.textContent = data.title || data.filename;
            card.appendChild(title);

            const fields = [
                { label: 'Заказчик', value: data.customer },
                { label: 'Разработчик', value: data.developer },
                { label: 'Год', value: data.year },
                { label: 'Тип', value: data.document_type },
                { label: 'Содержание', value: data.content_summary },
                { label: 'Цель', value: data.purpose }
            ];

            fields.forEach(f => {
                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'field';

                const labelSpan = document.createElement('span');
                labelSpan.className = 'field-label';
                labelSpan.textContent = f.label + ':';

                const valueSpan = document.createElement('span');
                valueSpan.className = 'field-value';
                valueSpan.textContent = f.value || '-';

                fieldDiv.appendChild(labelSpan);
                fieldDiv.appendChild(valueSpan);
                card.appendChild(fieldDiv);
            });

            grid.appendChild(card);
        }

        async function downloadReport() {
            const response = await fetch('/generate-md', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({results: lastResults})
            });
            const data = await response.json();
            if (data.success) {
                alert('Отчёт успешно создан: ' + data.filepath);
            }
        }
    </script>
</body>
</html>
    '''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    ext = filename.split('.')[-1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        file.save(tmp.name)
        tmp_path = Path(tmp.name)

    try:
        if ext == 'pdf':
            res = analyzer.analyze_pdf(tmp_path, file.filename)
        elif ext == 'docx':
            res = analyzer.analyze_docx(tmp_path, file.filename)
        elif ext == 'xml':
            res = analyzer.analyze_xml(tmp_path, file.filename)
        else:
            return jsonify({'error': 'Unsupported format'}), 400

        return jsonify(res)
    finally:
        if tmp_path.exists():
            os.remove(tmp_path)

@app.route('/generate-md', methods=['POST'])
def generate_md():
    try:
        data = request.get_json()
        results = data.get('results', [])

        tests_dir = Path(__file__).parent.parent / "Тесты_md"
        tests_dir.mkdir(exist_ok=True)

        filepath = generate_md_report(results, tests_dir)

        return jsonify({'success': True, 'filepath': filepath})
    except Exception as e:
        logger.error(f"MD generation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == "__main__":
    print("🚀 Сервер запущен: http://localhost:5006")
    print("📁 MD отчёты сохраняются в: Тесты_md/")
    app.run(host='127.0.0.1', port=5006, debug=False)
