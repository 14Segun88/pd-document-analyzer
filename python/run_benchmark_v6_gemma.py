#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
БЕНЧМАРК V6 GEMMA: Прогон всех документов через LLM Gemma 4-31B
"""

import os
import sys
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).parent / "v6"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DocumentAnalyzerGemma:
    """Анализатор с Gemma 4-31B"""
    
    def __init__(self):
        self.api_url = "http://192.168.47.22:1234/v1/chat/completions"
        self.model_name = "gemma-4-31b-it"
        self.kb_data = []
        
        kb_path = Path("/home/segun/CascadeProjects/Перед 0_2/json/knowledge_base.json")
        if kb_path.exists():
            with open(kb_path, 'r', encoding='utf-8') as f:
                self.kb_data = json.load(f)
            logger.info(f"KB loaded: {len(self.kb_data)} entries")
    
    def _extract_text_from_pdf(self, filepath: str) -> str:
        """Извлекает текст из PDF"""
        try:
            import fitz
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text[:5000]
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return ""
    
    def _extract_text_from_xml(self, filepath: str) -> str:
        """Извлекает текст из XML"""
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(filepath)
            root = tree.getroot()
            text = ET.tostring(root, encoding='unicode', method='text')
            return text[:5000]
        except Exception as e:
            logger.error(f"XML extraction error: {e}")
            return ""
    
    def _call_llm(self, text: str, filename: str) -> Optional[Dict]:
        """Вызывает Gemma 4-31B"""
        
        system_prompt = """Ты — эксперт по анализу проектной документации.

ЗАДАЧА: Извлеки из документа 7 полей в JSON формате.

ПРАВИЛА:
- title: полное название документа с шифром
- customer: заказчик
- developer: разработчик с городом
- year: год (из шифра /25 → 2025)
- document_type: тип документа
- content_summary: краткое описание 2-3 предложения
- purpose: цель документа

ВЕРНИ JSON БЕЗ MARKDOWN:
{"title": "...", "customer": "...", "developer": "...", "year": "...", "document_type": "...", "content_summary": "...", "purpose": "..."}"""
        
        import requests
        
        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"ТЕКСТ ДОКУМЕНТА:\n{text[:3000]}"}
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.1
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result_text = response.json()['choices'][0]['message']['content']
                
                # Парсим JSON
                result_text = re.sub(r'```json\s*', '', result_text)
                result_text = re.sub(r'```\s*', '', result_text)
                
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                    json_str = result_text[start_idx:end_idx+1]
                    result = json.loads(json_str)
                    return result
            else:
                logger.error(f"LLM API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"LLM call error: {e}")
            return None
    
    def analyze_pdf(self, filepath: str, filename: str) -> Optional[Dict]:
        """Анализирует PDF документ"""
        text = self._extract_text_from_pdf(filepath)
        if not text:
            return None
        return self._call_llm(text, filename)
    
    def analyze_xml(self, filepath: str, filename: str) -> Optional[Dict]:
        """Анализирует XML документ"""
        text = self._extract_text_from_xml(filepath)
        if not text:
            return None
        return self._call_llm(text, filename)


def find_etalon_in_kb(filename: str, kb_data: List[Dict]) -> Optional[Dict]:
    file_section = re.search(r'ПД[№\s]*(\d+)', filename)
    file_code = re.search(r'(МКД-\d{4}-\d{4}|МЕС-БМК-\d{2}[/_-]\d{2}|\d{2,4}/\d{2,4})', filename)
    
    best_match = None
    best_score = 0
    
    for entry in kb_data:
        kb_title = entry.get('title', '')
        score = 0
        
        if file_code:
            file_code_norm = file_code.group(1).replace('_', '-').replace('/', '-')
            kb_code = re.search(r'(МКД-\d{4}-\d{4}|МЕС-БМК-\d{2}-\d{2}|\d{2,4}/\d{2,4})', kb_title)
            if kb_code:
                kb_code_norm = kb_code.group(1).replace('/', '-')
                if file_code_norm in kb_code_norm or kb_code_norm in file_code_norm:
                    score += 50
        
        if file_section:
            section = file_section.group(1)
            if f'Раздел {section}' in kb_title or f'Раздел{section}' in kb_title:
                score += 30
        
        if 'ИОС' in filename:
            ios_match = re.search(r'ИОС(\d+\.?\d*)', filename)
            if ios_match:
                ios_num = ios_match.group(1)
                if f'ИОС{ios_num}' in kb_title or f'подраздел {ios_num}' in kb_title.lower():
                    score += 20
        
        if score > best_score:
            best_score = score
            best_match = entry
    
    if not best_match:
        filename_lower = filename.lower()
        for entry in kb_data:
            kb_title = entry.get('title', '').lower()
            
            if ('егрн' in filename_lower or 'выписка' in filename_lower) and ('егрн' in kb_title or 'выписка' in kb_title):
                best_match = entry
                break
            elif 'гпзу' in filename_lower and 'гпзу' in kb_title:
                best_match = entry
                break
            elif 'доверен' in filename_lower and 'доверен' in kb_title:
                best_match = entry
                break
            elif 'программа' in filename_lower and 'программа' in kb_title:
                best_match = entry
                break
            elif 'тз' in filename_lower and ('тз' in kb_title or 'задание' in kb_title):
                best_match = entry
                break
            elif ('ту' in filename_lower or 'условия' in filename_lower) and ('ту' in kb_title or 'условия' in kb_title):
                best_match = entry
                break
    
    return best_match


def generate_md_report(filename: str, llm_result: Dict, etalon: Optional[Dict], timestamp: str) -> str:
    md = f"""# Анализ документа: {filename}

**Дата анализа:** {timestamp}
**Модель:** Gemma 4-31B (gemma-4-31b-it)

---

## Результат LLM

| Поле | Значение |
|------|----------|
| **Название** | {llm_result.get('title', '—')} |
| **Заказчик** | {llm_result.get('customer', '—')} |
| **Подрядчик** | {llm_result.get('developer', '—')} |
| **Год** | {llm_result.get('year', '—')} |
| **Тип** | {llm_result.get('document_type', '—')} |
| **Содержимое** | {llm_result.get('content_summary', '—')} |
| **Цель** | {llm_result.get('purpose', '—')} |

---

## Эталон из KB

"""
    
    if etalon:
        md += f"""| Поле | Значение |
|------|----------|
| **Название** | {etalon.get('title', '—')} |
| **Заказчик** | {etalon.get('customer', '—')} |
| **Подрядчик** | {etalon.get('developer', '—')} |
| **Год** | {etalon.get('year', '—')} |
| **Тип** | {etalon.get('document_type', '—')} |
| **Содержимое** | {etalon.get('content_summary', '—')} |
| **Цель** | {etalon.get('purpose', '—')} |

---
"""
    else:
        md += "**Эталон не найден в KB**\n\n---\n"
    
    md += "\n## Сравнение LLM vs Эталон\n\n"
    
    if etalon:
        fields = ['title', 'customer', 'developer', 'year', 'document_type', 'content_summary', 'purpose']
        
        for field in fields:
            llm_val = str(llm_result.get(field, '')).strip()
            etalon_val = str(etalon.get(field, '')).strip()
            
            llm_norm = llm_val.lower().strip()
            etalon_norm = etalon_val.lower().strip()
            
            if llm_norm == etalon_norm and llm_norm:
                status = "OK"
            elif not etalon_norm or etalon_val == '—':
                status = "NO_ETALON"
            elif llm_norm in etalon_norm or etalon_norm in llm_norm:
                status = "PARTIAL"
            else:
                status = "FAIL"
            
            md += f"**{field}:** {status}\n"
            md += f"- LLM: {llm_val if llm_val else '—'}\n"
            md += f"- Эталон: {etalon_val if etalon_val else '—'}\n\n"
    else:
        md += "**Сравнение невозможно: эталон не найден**\n"
    
    return md


def main():
    logger.info("=" * 80)
    logger.info("BENCHMARK V6 GEMMA: Processing all documents")
    logger.info("=" * 80)
    
    input_dir = Path("/home/segun/CascadeProjects/Перед 0_2/Перед 0/Isxodnie_documenti/Анализ пакета 1")
    output_dir = Path("/home/segun/CascadeProjects/Перед 0_2/Тесты_md/Тесты_md2-Gemma")
    kb_path = Path("/home/segun/CascadeProjects/Перед 0_2/json/knowledge_base.json")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(kb_path, 'r', encoding='utf-8') as f:
        kb_data = json.load(f)
    
    logger.info(f"KB loaded: {len(kb_data)} entries")
    
    analyzer = DocumentAnalyzerGemma()
    logger.info(f"DocumentAnalyzerGemma initialized")
    logger.info(f"  Model: {analyzer.model_name}")
    logger.info(f"  API: {analyzer.api_url}")
    
    all_files = []
    for f in input_dir.iterdir():
        if f.suffix.lower() in ['.pdf', '.xml']:
            all_files.append(f)
    
    logger.info(f"Files found: {len(all_files)}")
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    results = []
    success_count = 0
    error_count = 0
    
    for i, filepath in enumerate(sorted(all_files), 1):
        filename = filepath.name
        
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"[{i}/{len(all_files)}] Processing: {filename}")
        logger.info("=" * 80)
        
        try:
            if filepath.suffix.lower() == '.pdf':
                result = analyzer.analyze_pdf(str(filepath), filename)
            elif filepath.suffix.lower() == '.xml':
                result = analyzer.analyze_xml(str(filepath), filename)
            else:
                continue
            
            if not result:
                logger.error(f"Empty result")
                error_count += 1
                continue
            
            etalon = find_etalon_in_kb(filename, kb_data)
            
            md_content = generate_md_report(
                filename=filename,
                llm_result=result,
                etalon=etalon,
                timestamp=timestamp
            )
            
            safe_filename = filename.replace('/', '_').replace('\\', '_').replace(' ', '_').replace('(', '_').replace(')', '_')
            md_filename = f"analysis_{timestamp}_{safe_filename}.md"
            md_path = output_dir / md_filename
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            logger.info(f"Saved: {md_filename}")
            success_count += 1
            
            results.append({
                'filename': filename,
                'llm_result': result,
                'etalon': etalon,
                'md_path': str(md_path)
            })
            
        except Exception as e:
            logger.error(f"Error: {e}")
            error_count += 1
            results.append({
                'filename': filename,
                'error': str(e)
            })
    
    summary_path = output_dir / f"SUMMARY_{timestamp}.md"
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"# Summary: BENCHMARK V6 GEMMA\n\n")
        f.write(f"**Date:** {timestamp}\n\n")
        f.write(f"**Model:** Gemma 4-31B (gemma-4-31b-it)\n\n")
        f.write(f"**Total files:** {len(all_files)}\n\n")
        f.write(f"**Success:** {success_count}\n\n")
        f.write(f"**Errors:** {error_count}\n\n")
        f.write("---\n\n")
        
        for result in results:
            filename = result['filename']
            if 'error' in result:
                f.write(f"ERROR: **{filename}** - {result['error']}\n\n")
            else:
                md_path = Path(result['md_path']).name
                f.write(f"OK: **{filename}** - [{md_path}]({md_path})\n\n")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"COMPLETED!")
    logger.info("=" * 80)
    logger.info(f"Success: {success_count}/{len(all_files)}")
    logger.info(f"Errors: {error_count}/{len(all_files)}")
    logger.info(f"Summary: {summary_path}")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
