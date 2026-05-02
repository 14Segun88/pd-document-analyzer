#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAIR BENCHMARK: Mistral 14B Reasoning vs Gemma 4-31B
Одинаковые условия для обеих моделей — параметры V6 (CoT + KB + Override):
  - Temperature: 0.01
  - Max tokens:  8000
  - Timeout:     180 сек
  - System prompt: CoT + KB примеры (3 шт.)
  - KB Override:   ON (score > 0.90)
  - Текст:         первые 3000 символов
"""

import os, sys, json, logging, re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

import requests
import fitz  # pymupdf
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# КОНФИГУРАЦИЯ
# ─────────────────────────────────────────────
API_URL    = "http://192.168.47.22:1234/v1/chat/completions"
MODELS     = {
    "mistral": "mistralai/ministral-3-14b-reasoning",
    "gemma":   "gemma-4-31b-it",
}
TEMPERATURE = 0.01
MAX_TOKENS  = 8000
TIMEOUT     = 180
TEXT_LIMIT  = 3000

INPUT_DIR = Path("/home/segun/CascadeProjects/Перед 0_2/Перед 0/Isxodnie_documenti/Анализ пакета 1")
KB_PATH   = Path("/home/segun/CascadeProjects/Перед 0_2/json/knowledge_base.json")

OUTPUT_MISTRAL = Path("/home/segun/CascadeProjects/Перед 0_2/Тесты_md")
OUTPUT_GEMMA   = Path("/home/segun/CascadeProjects/Перед 0_2/Тесты_md/Тесты_md2-Gemma")

# ─────────────────────────────────────────────
# SYSTEM PROMPT (одинаковый для обеих моделей)
# ─────────────────────────────────────────────
COT_SYSTEM_PROMPT = """Ты — эксперт по анализу проектной документации.

ПРИМЕРЫ ИЗ БАЗЫ ЗНАНИЙ:
{kb_examples}

ЗАДАЧА: Извлеки из документа 7 полей в JSON формате.

ПРАВИЛА:
- title: полное название документа с шифром (например: "Раздел 3 АР (157/25-АР)")
- customer: заказчик (например: "ГКУ МО «ДЗКС»")
- developer: разработчик с городом (например: "ООО «Мосрегионпроект», г. Электросталь")
- year: год (из шифра /25 → 2025)
- document_type: тип (Раздел, Пояснительная записка, ТУ, Договор)
- content_summary: краткое описание 2-3 предложения
- purpose: цель документа

ВЕРНИ JSON БЕЗ MARKDOWN:
{"title": "...", "customer": "...", "developer": "...", "year": "...", "document_type": "...", "content_summary": "...", "purpose": "..."}
"""

# ─────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (общие для обеих)
# ─────────────────────────────────────────────

def load_kb() -> List[Dict]:
    with open(KB_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_text_pdf(filepath: str) -> str:
    try:
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
            if len(text) > TEXT_LIMIT:
                break
        doc.close()
        return text[:TEXT_LIMIT]
    except Exception as e:
        logger.error(f"PDF extract error: {e}")
        return ""


def extract_text_xml(filepath: str) -> str:
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        text = ' '.join(t.text for t in root.iter() if t.text)
        return text[:TEXT_LIMIT]
    except Exception as e:
        logger.error(f"XML extract error: {e}")
        return ""


def extract_code_from_filename(filename: str) -> Optional[str]:
    for pattern in [
        r'([А-Я]{2,4}-\d{4}-\d{4})',
        r'([А-Я]{2,4}-[А-Я]{2,4}[\-_\.]\d{2}[\-_\.]\d{2})',
        r'([А-Я]{2,4}_[А-Я]{2,4}_\d{2}_\d{2})',
        r'([А-Я]{2,4}-[А-Я]{2,4}-\d{2}/\d{2})',
        r'(\d{2,4}/\d{2,4})',
    ]:
        m = re.search(pattern, filename)
        if m:
            return m.group(1).replace('_', '-').replace('.', '-')
    return None


def calculate_score(filename: str, kb_title: str) -> float:
    score = SequenceMatcher(None, filename.lower(), kb_title.lower()).ratio()

    file_section = re.search(r'ПД№(\d+)', filename)
    kb_section   = re.search(r'Раздел\s*(\d+)', kb_title)
    file_code    = extract_code_from_filename(filename)
    kb_code      = extract_code_from_filename(kb_title)

    if file_code: file_code = file_code.replace('/', '-')
    if kb_code:   kb_code   = kb_code.replace('/', '-')

    if file_section and kb_section and file_section.group(1) == kb_section.group(1):
        if file_code and kb_code and file_code == kb_code:
            score = max(score, 0.99)
        else:
            score = max(score, 0.70)

    if file_code and kb_code and file_code == kb_code:
        score = max(score, 0.90)

    if 'АР'  in filename and 'АР'  in kb_title: score = max(score, 0.75)
    if 'КР'  in filename and 'КР'  in kb_title: score = max(score, 0.75)
    if 'ПБ'  in filename and ('ПБ' in kb_title or 'пожарн' in kb_title.lower()): score = max(score, 0.85)
    if 'ОДИ' in filename and 'ОДИ' in kb_title: score = max(score, 0.85)

    return score


def get_kb_override(filename: str, kb_data: List[Dict]) -> Optional[Dict]:
    """KB Override: если score > 0.90 — берём purpose/summary/type из KB."""
    best_score, best_entry = 0.0, None
    for entry in kb_data:
        s = calculate_score(filename, entry.get('title', ''))
        if s > best_score:
            best_score, best_entry = s, entry
    if best_entry and best_score > 0.90:
        logger.info(f"  KB Override ({int(best_score*100)}%): {best_entry.get('title','')[:40]}")
        return {
            'purpose':         best_entry.get('purpose'),
            'content_summary': best_entry.get('content_summary'),
            'document_type':   best_entry.get('document_type'),
        }
    return None


def get_kb_examples(filename: str, text: str, kb_data: List[Dict]) -> str:
    """Семантический подбор 3 примеров из KB."""
    def tokenize(s):
        return set(re.findall(r'[а-яА-Яa-zA-Z0-9]+', s.lower()))

    tokens = tokenize(filename) | tokenize(text[:500])
    scored = []
    for entry in kb_data:
        src    = entry.get('_source_doc', '')
        title  = entry.get('title', '')
        dtype  = entry.get('document_type', '')
        esc    = tokenize(src + " " + title + " " + dtype)
        s = len(tokens & esc)
        if s > 0:
            scored.append((s, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    top3 = [e for _, e in scored[:3]]

    if not top3:
        return "ПРИМЕРЫ НЕ НАЙДЕНЫ. Используй СТРУКТУРУ из инструкции выше."

    parts = []
    for i, ex in enumerate(top3, 1):
        clean = {k: v for k, v in ex.items() if not k.startswith('_')}
        parts.append(f"ПРИМЕР {i}:\n{json.dumps(clean, ensure_ascii=False, indent=2)}")
    return "\n\n".join(parts)


def call_llm(model_name: str, text: str, filename: str, kb_data: List[Dict]) -> Optional[Dict]:
    """Единый вызов LLM — одинаков для Mistral и Gemma."""
    kb_override = get_kb_override(filename, kb_data)
    kb_examples = get_kb_examples(filename, text, kb_data)
    prompt = COT_SYSTEM_PROMPT.replace("{kb_examples}", kb_examples)

    try:
        response = requests.post(
            API_URL,
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user",   "content": f"ТЕКСТ ДОКУМЕНТА:\n{text[:TEXT_LIMIT]}"},
                ],
                "max_tokens":  MAX_TOKENS,
                "temperature": TEMPERATURE,
            },
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            msg = response.json()['choices'][0]['message']
            result_text = msg.get('content') or msg.get('reasoning_content', '')

            if not result_text:
                return None

            result_text = re.sub(r'```json\s*', '', result_text)
            result_text = re.sub(r'```\s*',     '', result_text)

            s = result_text.find('{')
            e = result_text.rfind('}')
            if s != -1 and e != -1 and s < e:
                result = json.loads(result_text[s:e+1])

                # KB Override (одинаково для обеих)
                if kb_override:
                    for key in ['purpose', 'content_summary', 'document_type']:
                        if kb_override.get(key):
                            result[key] = kb_override[key]
                return result
        else:
            logger.error(f"API error {response.status_code}: {response.text[:200]}")
    except Exception as ex:
        logger.error(f"LLM call error: {ex}")
    return None


# ─────────────────────────────────────────────
# ETALON MATCHING (одинаковый)
# ─────────────────────────────────────────────

def find_etalon(filename: str, kb_data: List[Dict]) -> Optional[Dict]:
    # Direct _source_doc match first
    for entry in kb_data:
        if entry.get('_source_doc', '') == filename:
            return entry

    # Score-based match
    best_score, best_match = 0, None
    for entry in kb_data:
        s = calculate_score(filename, entry.get('title', ''))
        if s > best_score:
            best_score, best_match = s, entry
    if best_score > 0.60:
        return best_match
    return None


# ─────────────────────────────────────────────
# REPORT GENERATION
# ─────────────────────────────────────────────

def generate_md_report(filename: str, model_label: str, llm_result: Dict,
                       etalon: Optional[Dict], timestamp: str) -> str:
    def v(d, k): return (d or {}).get(k, '—') or '—'

    md = f"""# Анализ документа: {filename}

**Дата анализа:** {timestamp}
**Модель:** {model_label}

---

## Результат LLM

| Поле | Значение |
|------|----------|
| **Название** | {v(llm_result,'title')} |
| **Заказчик** | {v(llm_result,'customer')} |
| **Подрядчик** | {v(llm_result,'developer')} |
| **Год** | {v(llm_result,'year')} |
| **Тип** | {v(llm_result,'document_type')} |
| **Содержимое** | {v(llm_result,'content_summary')} |
| **Цель** | {v(llm_result,'purpose')} |

---

## Эталон из KB

"""
    if etalon:
        md += f"""| Поле | Значение |
|------|----------|
| **Название** | {v(etalon,'title')} |
| **Заказчик** | {v(etalon,'customer')} |
| **Подрядчик** | {v(etalon,'developer')} |
| **Год** | {v(etalon,'year')} |
| **Тип** | {v(etalon,'document_type')} |
| **Содержимое** | {v(etalon,'content_summary')} |
| **Цель** | {v(etalon,'purpose')} |

---
"""
    else:
        md += "**Эталон не найден в KB**\n\n---\n"

    md += "\n## Сравнение LLM vs Эталон\n\n"
    if etalon:
        for field in ['title','customer','developer','year','document_type','content_summary','purpose']:
            lv = str(v(llm_result, field)).lower().strip()
            ev = str(v(etalon, field)).lower().strip()
            if lv == ev and lv not in ('—', 'none', ''):
                status = "✅ OK"
            elif not ev or ev in ('—', 'none'):
                status = "⬜ NO_ETALON"
            elif lv in ev or ev in lv:
                status = "🟡 PARTIAL"
            else:
                status = "❌ FAIL"
            md += f"**{field}:** {status}\n"
            md += f"- LLM: {v(llm_result,field)}\n"
            md += f"- Эталон: {v(etalon,field)}\n\n"
    else:
        md += "**Сравнение невозможно: эталон не найден**\n"

    return md


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def run_for_model(model_key: str, model_name: str, output_dir: Path,
                  all_files: List[Path], kb_data: List[Dict], timestamp: str):

    model_label = f"{model_key.capitalize()} — {model_name}"
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"STARTING: {model_label}")
    logger.info(f"  temperature={TEMPERATURE}, max_tokens={MAX_TOKENS}, timeout={TIMEOUT}s")
    logger.info(f"  KB examples: 3 | KB Override: ON (score>0.90) | text_limit={TEXT_LIMIT}")
    logger.info("=" * 80)

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    success_count = error_count = 0

    for i, filepath in enumerate(sorted(all_files), 1):
        filename = filepath.name
        logger.info(f"\n[{i}/{len(all_files)}] {filename}")

        try:
            if filepath.suffix.lower() == '.pdf':
                text = extract_text_pdf(str(filepath))
            elif filepath.suffix.lower() == '.xml':
                text = extract_text_xml(str(filepath))
            else:
                continue

            llm_result = call_llm(model_name, text, filename, kb_data)

            if not llm_result:
                logger.warning(f"  EMPTY result → saving None placeholder")
                llm_result = {k: None for k in
                    ['title','customer','developer','year','document_type','content_summary','purpose']}
                error_count += 1
            else:
                success_count += 1

            etalon = find_etalon(filename, kb_data)
            md = generate_md_report(filename, model_label, llm_result, etalon, timestamp)

            safe = re.sub(r'[/ \\()]', '_', filename)
            md_filename = f"analysis_{timestamp}_{safe}.md"
            md_path = output_dir / md_filename
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md)

            logger.info(f"  ✅ Saved: {md_filename}")
            results.append({'filename': filename, 'md_path': str(md_path)})

        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            error_count += 1
            results.append({'filename': filename, 'error': str(e)})

    # Summary
    summary_path = output_dir / f"SUMMARY_{timestamp}.md"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"# Summary: FAIR BENCHMARK — {model_key.upper()}\n\n")
        f.write(f"**Date:** {timestamp}\n\n")
        f.write(f"**Model:** {model_name}\n\n")
        f.write(f"**Conditions:** temperature={TEMPERATURE}, max_tokens={MAX_TOKENS}, "
                f"timeout={TIMEOUT}s, text_limit={TEXT_LIMIT}, KB_examples=3, KB_override=ON\n\n")
        f.write(f"**Total files:** {len(all_files)}\n\n")
        f.write(f"**Success:** {success_count}\n\n")
        f.write(f"**Errors (empty/None):** {error_count}\n\n")
        f.write("---\n\n")
        for r in results:
            fn = r['filename']
            if 'error' in r:
                f.write(f"ERROR: **{fn}** — {r['error']}\n\n")
            else:
                mdname = Path(r['md_path']).name
                f.write(f"OK: **{fn}** — [{mdname}]({mdname})\n\n")

    logger.info(f"\nDone {model_key}: {success_count}/{len(all_files)} OK, {error_count} empty")
    logger.info(f"Summary: {summary_path}")


def main():
    logger.info("=" * 80)
    logger.info("FAIR BENCHMARK V6: Mistral 14B Reasoning vs Gemma 4-31B")
    logger.info("IDENTICAL conditions for both models")
    logger.info("=" * 80)

    kb_data = load_kb()
    logger.info(f"KB loaded: {len(kb_data)} entries")

    all_files = sorted([f for f in INPUT_DIR.iterdir()
                        if f.suffix.lower() in ('.pdf', '.xml')])
    logger.info(f"Files to process: {len(all_files)}")

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    # Run Mistral first
    run_for_model("mistral", MODELS["mistral"], OUTPUT_MISTRAL, all_files, kb_data, timestamp)

    # Run Gemma second (same timestamp → easy to compare side-by-side)
    run_for_model("gemma", MODELS["gemma"], OUTPUT_GEMMA, all_files, kb_data, timestamp)

    logger.info("\n" + "=" * 80)
    logger.info("FAIR BENCHMARK COMPLETE")
    logger.info(f"Mistral results: {OUTPUT_MISTRAL}")
    logger.info(f"Gemma   results: {OUTPUT_GEMMA}")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
