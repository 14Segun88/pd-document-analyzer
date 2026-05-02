#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAIR BENCHMARK — Пакет 2: Mistral 14B Reasoning vs Gemma 4-31B
Условия идентичны параметрам V6:
  temp=0.01 | max_tokens=8000 | timeout=180s
  CoT + KB примеры (3 шт.) | KB Override ON | text=3000 chars
"""

import os, re, json, logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import requests
import fitz
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─── КОНФИГУРАЦИЯ ───────────────────────────────────────────────
API_URL    = "http://192.168.47.22:1234/v1/chat/completions"
MODELS     = {
    "mistral": "mistralai/ministral-3-14b-reasoning",
    "gemma":   "gemma-4-31b-it",
}
TEMPERATURE = 0.01
MAX_TOKENS  = 8000
TIMEOUT     = 180
TEXT_LIMIT  = 3000

INPUT_DIR      = Path("/home/segun/CascadeProjects/Перед 0_2/Перед 0/Isxodnie_documenti/Анализ пакета 2")
KB_PATH        = Path("/home/segun/CascadeProjects/Перед 0_2/json/knowledge_base.json")
OUTPUT_MISTRAL = Path("/home/segun/CascadeProjects/Перед 0_2/Тесты_md/Пакет2-Mistral")
OUTPUT_GEMMA   = Path("/home/segun/CascadeProjects/Перед 0_2/Тесты_md/Пакет2-Gemma")

# ─── SYSTEM PROMPT (одинаковый) ─────────────────────────────────
COT_SYSTEM_PROMPT = """Ты — эксперт по анализу проектной документации.

ПРИМЕРЫ ИЗ БАЗЫ ЗНАНИЙ:
{kb_examples}

ЗАДАЧА: Извлеки из документа 7 полей в JSON формате.

ПРАВИЛА:
- title: полное название документа с шифром (например: "Раздел 3 АР (157/25-АР)")
- customer: заказчик (например: "ГКУ МО «ДЗКС»")
- developer: разработчик с городом (например: "ООО «Мосрегионпроект», г. Электросталь")
- year: год (из шифра /25 → 2025)
- document_type: тип (Раздел, Пояснительная записка, ТУ, Договор, ИУЛ)
- content_summary: краткое описание 2-3 предложения
- purpose: цель документа

ВЕРНИ JSON БЕЗ MARKDOWN:
{"title": "...", "customer": "...", "developer": "...", "year": "...", "document_type": "...", "content_summary": "...", "purpose": "..."}
"""

# ─── ВСПОМОГАТЕЛЬНЫЕ ────────────────────────────────────────────

def load_kb() -> List[Dict]:
    with open(KB_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    logger.info(f"KB loaded: {len(data)} entries")
    return data


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


def extract_code(name: str) -> Optional[str]:
    for pat in [
        r'([А-Я]{2,4}-\d{4}-\d{4})',
        r'([А-Я]{2,4}-[А-Я]{2,4}[\-_\.]\d{2}[\-_\.]\d{2})',
        r'([А-Я]{2,4}_[А-Я]{2,4}_\d{2}_\d{2})',
        r'(\d{2,4}[-/]\d{2,4})',
    ]:
        m = re.search(pat, name)
        if m:
            return m.group(1).replace('_', '-').replace('.', '-')
    return None


def calc_score(filename: str, kb_title: str) -> float:
    score = SequenceMatcher(None, filename.lower(), kb_title.lower()).ratio()
    fc = extract_code(filename)
    kc = extract_code(kb_title)
    if fc: fc = fc.replace('/', '-')
    if kc: kc = kc.replace('/', '-')
    if fc and kc and fc == kc:
        score = max(score, 0.90)
    # Section number boost
    fs = re.search(r'№\s*(\d+)', filename)
    ks = re.search(r'Раздел\s*(\d+)', kb_title)
    if fs and ks and fs.group(1) == ks.group(1):
        score = max(score, 0.70)
    # Type boosts
    for kw in ['АР', 'КР', 'ПБ', 'ОДИ', 'ТХ', 'ПОС', 'ПМООС', 'ТБЭ', 'ИГДИ', 'ИОС']:
        if kw in filename and kw in kb_title:
            score = max(score, 0.75)
    if 'СОШ' in filename and 'СОШ' in kb_title:
        score = max(score, 0.80)
    return score


def kb_override(filename: str, kb_data: List[Dict]) -> Optional[Dict]:
    best_s, best_e = 0.0, None
    for e in kb_data:
        s = calc_score(filename, e.get('title', ''))
        if s > best_s:
            best_s, best_e = s, e
    if best_e and best_s > 0.90:
        logger.info(f"  KB Override ({int(best_s*100)}%): {best_e.get('title','')[:50]}")
        return {k: best_e.get(k) for k in ['purpose', 'content_summary', 'document_type']}
    return None


def kb_examples(filename: str, text: str, kb_data: List[Dict]) -> str:
    def tok(s): return set(re.findall(r'[а-яА-Яa-zA-Z0-9]+', s.lower()))
    tokens = tok(filename) | tok(text[:500])
    scored = []
    for e in kb_data:
        et = tok(e.get('_source_doc','') + ' ' + e.get('title','') + ' ' + e.get('document_type',''))
        s = len(tokens & et)
        if s > 0:
            scored.append((s, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    top3 = [e for _, e in scored[:3]]
    if not top3:
        return "ПРИМЕРЫ НЕ НАЙДЕНЫ."
    parts = []
    for i, ex in enumerate(top3, 1):
        clean = {k: v for k, v in ex.items() if not k.startswith('_')}
        parts.append(f"ПРИМЕР {i}:\n{json.dumps(clean, ensure_ascii=False, indent=2)}")
    return "\n\n".join(parts)


def call_llm(model_name: str, text: str, filename: str, kb_data: List[Dict]) -> Optional[Dict]:
    override = kb_override(filename, kb_data)
    examples = kb_examples(filename, text, kb_data)
    prompt = COT_SYSTEM_PROMPT.replace("{kb_examples}", examples)
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
            result_text = re.sub(r'```\s*', '', result_text)
            s = result_text.find('{')
            e = result_text.rfind('}')
            if s != -1 and e != -1 and s < e:
                result = json.loads(result_text[s:e+1])
                if override:
                    for k in ['purpose', 'content_summary', 'document_type']:
                        if override.get(k):
                            result[k] = override[k]
                return result
        else:
            logger.error(f"API {response.status_code}: {response.text[:200]}")
    except Exception as ex:
        logger.error(f"LLM error: {ex}")
    return None


def find_etalon(filename: str, kb_data: List[Dict]) -> Optional[Dict]:
    # Direct match first
    for e in kb_data:
        if e.get('_source_doc', '') == filename:
            return e
    # Score match
    best_s, best_e = 0.0, None
    for e in kb_data:
        s = calc_score(filename, e.get('title', ''))
        if s > best_s:
            best_s, best_e = s, e
    return best_e if best_s > 0.55 else None


def gen_report(filename: str, model_label: str, llm: Dict,
               etalon: Optional[Dict], ts: str) -> str:
    def v(d, k): return (d or {}).get(k) or '—'

    md = f"""# Анализ документа: {filename}

**Дата анализа:** {ts}
**Модель:** {model_label}

---

## Результат LLM

| Поле | Значение |
|------|----------|
| **Название** | {v(llm,'title')} |
| **Заказчик** | {v(llm,'customer')} |
| **Подрядчик** | {v(llm,'developer')} |
| **Год** | {v(llm,'year')} |
| **Тип** | {v(llm,'document_type')} |
| **Содержимое** | {v(llm,'content_summary')} |
| **Цель** | {v(llm,'purpose')} |

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
            lv = str(v(llm, field)).lower().strip()
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
            md += f"- LLM: {v(llm,field)}\n"
            md += f"- Эталон: {v(etalon,field)}\n\n"
    else:
        md += "**Сравнение невозможно: эталон не найден**\n"
    return md


# ─── MAIN ───────────────────────────────────────────────────────

def run_model(model_key: str, model_name: str, output_dir: Path,
              all_files: List[Path], kb_data: List[Dict], ts: str):
    label = f"{model_key.upper()} — {model_name}"
    logger.info("\n" + "="*80)
    logger.info(f"START: {label}")
    logger.info(f"  temp={TEMPERATURE} | max_tokens={MAX_TOKENS} | timeout={TIMEOUT}s | KB Override ON")
    logger.info("="*80)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    ok_count = err_count = 0

    for i, fp in enumerate(sorted(all_files), 1):
        fname = fp.name
        logger.info(f"\n[{i}/{len(all_files)}] {fname}")
        try:
            text = extract_text_pdf(str(fp))
            llm_result = call_llm(model_name, text, fname, kb_data)
            if not llm_result:
                logger.warning("  EMPTY result")
                llm_result = {k: None for k in
                    ['title','customer','developer','year','document_type','content_summary','purpose']}
                err_count += 1
            else:
                ok_count += 1

            etalon = find_etalon(fname, kb_data)
            md = gen_report(fname, label, llm_result, etalon, ts)

            safe = re.sub(r'[/ \\()]', '_', fname)
            md_name = f"analysis_{ts}_{safe}.md"
            md_path = output_dir / md_name
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md)
            logger.info(f"  ✅ {md_name}")
            results.append({'filename': fname, 'md_path': str(md_path)})
        except Exception as ex:
            logger.error(f"  ❌ {ex}")
            err_count += 1
            results.append({'filename': fname, 'error': str(ex)})

    # Summary
    sum_path = output_dir / f"SUMMARY_{ts}.md"
    with open(sum_path, 'w', encoding='utf-8') as f:
        f.write(f"# FAIR BENCHMARK — ПАКЕТ 2 — {model_key.upper()}\n\n")
        f.write(f"**Date:** {ts}\n\n")
        f.write(f"**Model:** {model_name}\n\n")
        f.write(f"**Conditions:** temp={TEMPERATURE}, max_tokens={MAX_TOKENS}, "
                f"timeout={TIMEOUT}s, text_limit={TEXT_LIMIT}, KB_examples=3, KB_override=ON\n\n")
        f.write(f"**Total:** {len(all_files)} | **Success:** {ok_count} | **Errors:** {err_count}\n\n---\n\n")
        for r in results:
            if 'error' in r:
                f.write(f"ERROR: **{r['filename']}** — {r['error']}\n\n")
            else:
                mname = Path(r['md_path']).name
                f.write(f"OK: **{r['filename']}** — [{mname}]({mname})\n\n")

    logger.info(f"\nDone {model_key}: {ok_count}/{len(all_files)} OK, {err_count} empty/error")
    logger.info(f"Summary → {sum_path}")


def main():
    logger.info("="*80)
    logger.info("FAIR BENCHMARK V6 — ПАКЕТ 2")
    logger.info("Mistral 14B Reasoning vs Gemma 4-31B — одинаковые условия")
    logger.info("="*80)

    kb_data   = load_kb()
    all_files = sorted([f for f in INPUT_DIR.iterdir() if f.suffix.lower() == '.pdf'])
    logger.info(f"Files: {len(all_files)}")

    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    run_model("mistral", MODELS["mistral"], OUTPUT_MISTRAL, all_files, kb_data, ts)
    run_model("gemma",   MODELS["gemma"],   OUTPUT_GEMMA,   all_files, kb_data, ts)

    logger.info("\n" + "="*80)
    logger.info("COMPLETE")
    logger.info(f"  Mistral → {OUTPUT_MISTRAL}")
    logger.info(f"  Gemma   → {OUTPUT_GEMMA}")
    logger.info("="*80)


if __name__ == '__main__':
    main()
