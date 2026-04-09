#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Бенчмарк Пакет 1: Точность / Стабильность / Время
Сравнение 4 документов с эталоном из «Анализ Пакета_1.docx»
"""

import sys
import re
import time
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, str(Path('./.kilo/worktrees/playful-flower').absolute()))
from web_app_v5_final import DocumentAnalyzer
from docx import Document

# ═══════════════════════════════════════════════════════════════
# Жёсткий маппинг: Таблица в Word → Файл документа
# ═══════════════════════════════════════════════════════════════
BASE = Path('Перед 0/Isxodnie_documenti/Анализ пакета 1')
WORD_FILE = BASE / 'Анализ Пакета_1.docx'

TABLE_TO_FILE = {
    0: BASE / 'Раздел ПД1-ПЗ (7).xml',
    1: BASE / 'Раздел ПД3-АР.pdf',
    2: BASE / 'Раздел ПД4-КР.pdf',
    3: BASE / 'ТЗ.xml',
}

KEY_MAP = {
    'Название': 'title',
    'Заказчик': 'customer',
    'Подрядчик / проектная фирма': 'developer',
    'Год составления': 'year',
    'Тип документа': 'document_type',
    'Содержимое': 'content_summary',
    'Цель': 'purpose',
}

TARGET_KEYS = ['title', 'customer', 'developer', 'year', 'document_type', 'content_summary', 'purpose']


def load_references():
    doc = Document(WORD_FILE)
    refs = []
    for idx, table in enumerate(doc.tables):
        if idx not in TABLE_TO_FILE:
            continue
        ref = {}
        for row in table.rows:
            if len(row.cells) >= 2:
                key = row.cells[0].text.strip()
                val = row.cells[1].text.strip()
                mapped = KEY_MAP.get(key)
                if mapped:
                    ref[mapped] = val
        refs.append({
            'file': TABLE_TO_FILE[idx],
            'reference': ref,
        })
    return refs


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    a = re.sub(r'\s+', ' ', a.lower().strip())
    b = re.sub(r'\s+', ' ', b.lower().strip())
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.85
    return SequenceMatcher(None, a, b).ratio()


def run_pass(analyzer, refs):
    start = time.time()
    results = []
    for item in refs:
        fp = item['file']
        ext = fp.suffix.lower()
        if ext == '.pdf':
            res = analyzer.analyze_pdf(fp, fp.name)
        elif ext == '.xml':
            res = analyzer.analyze_xml(fp, fp.name)
        elif ext in ('.docx', '.doc'):
            res = analyzer.analyze_docx(fp, fp.name)
        else:
            continue

        scores = {}
        for key in TARGET_KEYS:
            ref_val = item['reference'].get(key, '')
            ext_val = str(res.get(key, '') or '')
            sim = similarity(ref_val, ext_val)
            scores[key] = {
                'ref': ref_val,
                'ext': ext_val,
                'sim': round(sim, 2),
                'ok': sim >= 0.5,
            }
        results.append({'file': fp.name, 'scores': scores})
    return results, time.time() - start


def main():
    NUM_RUNS = 1
    refs = load_references()
    print(f"📦 Пакет 1: {len(refs)} документов, {NUM_RUNS} прогонов\n")

    analyzer = DocumentAnalyzer()
    all_runs, times = [], []

    for i in range(NUM_RUNS):
        res, t = run_pass(analyzer, refs)
        all_runs.append(res)
        times.append(t)
        print(f"  Прогон {i+1}: {t:.2f}с")

    # ── Детальный вывод ──────────────────────────────────────
    first = all_runs[0]
    total, matched = 0, 0

    for item in first:
        print(f"\n{'─'*70}")
        print(f"📄 {item['file']}")
        print(f"{'─'*70}")
        for key in TARGET_KEYS:
            s = item['scores'][key]
            icon = "✅" if s['ok'] else "❌"
            pct = int(s['sim'] * 100)
            total += 1
            if s['ok']:
                matched += 1
            print(f"  {icon} {key:20s} [{pct:3d}%]")
            print(f"     Эталон : {s['ref'][:90]}")
            print(f"     Получ. : {s['ext'][:90]}")

    # ── Стабильность ──────────────────────────────────────────
    stability = 100.0
    if NUM_RUNS > 1:
        mismatches, comparisons = 0, 0
        for r in range(1, NUM_RUNS):
            for d in range(len(first)):
                for k in TARGET_KEYS:
                    comparisons += 1
                    if all_runs[0][d]['scores'][k]['ext'] != all_runs[r][d]['scores'][k]['ext']:
                        mismatches += 1
        stability = (comparisons - mismatches) / comparisons * 100

    accuracy = matched / total * 100 if total else 0
    avg_time = sum(times) / len(times)

    # ── ИТОГИ ─────────────────────────────────────────────────
    print(f"\n{'═'*70}")
    print(f"  ИТОГИ ПАКЕТ 1 ({len(refs)} документов × {len(TARGET_KEYS)} полей = {total} сравнений)")
    print(f"{'═'*70}")
    print(f"  📊 Точность:      {accuracy:.1f}%  ({matched}/{total})")
    print(f"  🔄 Стабильность:  {stability:.1f}%  ({NUM_RUNS} прогонов)")
    print(f"  ⏱️  Время:         {avg_time:.2f}с  ({avg_time/len(refs):.2f}с/док)")
    print(f"{'═'*70}")

    print("\n  По полям:")
    for key in TARGET_KEYS:
        ok = sum(1 for i in first if i['scores'][key]['ok'])
        pct = ok / len(first) * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"    {key:20s} {bar} {pct:5.1f}% ({ok}/{len(first)})")


if __name__ == '__main__':
    main()
