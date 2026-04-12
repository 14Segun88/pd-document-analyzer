#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cross_model_scorer.py
Сравнение выводов двух моделей (Mistral vs Gemma) на одних документах
без эталонов KB. Метод: семантическая близость ответов друг к другу.

"Насколько модели согласны между собой?"
"""

import os, re
from difflib import SequenceMatcher
from rapidfuzz import fuzz

# ─── КОНФИГУРАЦИЯ ─────────────────────────────────────────────
TS   = "2026-04-10_17-33-44"
MDIR = "Тесты_md/Пакет2-Mistral"
GDIR = "Тесты_md/Пакет2-Gemma"

THRESH_HIGH   = 85
THRESH_MEDIUM = 60

FIELDS = ['title', 'customer', 'developer', 'year',
          'document_type', 'content_summary', 'purpose']

FIELD_RU = {
    'title':           'Название',
    'customer':        'Заказчик',
    'developer':       'Подрядчик',
    'year':            'Год',
    'document_type':   'Тип',
    'content_summary': 'Содержимое',
    'purpose':         'Цель',
}

# ─── СЕМАНТИКА (V6-стиль) ──────────────────────────────────────

def semantic_sim(a: str, b: str) -> float:
    a = (a or '').strip()
    b = (b or '').strip()
    if not a or not b or a in ('—','None','') or b in ('—','None',''):
        return 0.0
    al, bl = a.lower(), b.lower()
    base = SequenceMatcher(None, al, bl).ratio() * 100
    ts   = fuzz.token_sort_ratio(al, bl)
    pr   = fuzz.partial_ratio(al, bl)
    wr   = fuzz.WRatio(al, bl)
    best = max(base, ts, pr, wr)
    # Бонус: аббревиатуры
    acr_a = set(re.findall(r'[А-ЯA-Z]{2,}', a))
    acr_b = set(re.findall(r'[А-ЯA-Z]{2,}', b))
    bonus = min(len(acr_a & acr_b) * 5, 15)
    # Бонус: год
    yr_a = set(re.findall(r'\b(20\d{2})\b', a))
    yr_b = set(re.findall(r'\b(20\d{2})\b', b))
    if yr_a & yr_b:
        bonus += 10
    return min(best + bonus, 100.0)


def label(sc: float, a: str, b: str) -> str:
    if not a or a in ('—','None','') or not b or b in ('—','None',''):
        return 'EMPTY'
    if sc >= THRESH_HIGH:   return '✅ AGREE'
    if sc >= THRESH_MEDIUM: return '🟡 CLOSE'
    return '❌ DIFFER'


# ─── ПАРСИНГ MD ФАЙЛОВ ────────────────────────────────────────

def parse_llm_table(content: str) -> dict:
    """Извлечь значения из таблицы ## Результат LLM"""
    idx = content.find('## Результат LLM')
    if idx == -1:
        return {}
    block = content[idx:idx+3000]
    result = {}
    field_map = {
        'Название': 'title', 'Заказчик': 'customer',
        'Подрядчик': 'developer', 'Год': 'year',
        'Тип': 'document_type', 'Содержимое': 'content_summary',
        'Цель': 'purpose',
    }
    for line in block.split('\n'):
        m = re.match(r'\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|', line)
        if m:
            key_ru = m.group(1).strip()
            val    = m.group(2).strip()
            if key_ru in field_map and val not in ('Значение', '', '-'):
                result[field_map[key_ru]] = val
    return result


def is_empty_result(vals: dict) -> bool:
    return all(v in ('—', 'None', '', None) for v in vals.values())


def load_dir(dirpath: str, ts: str) -> dict:
    files = [f for f in os.listdir(dirpath)
             if f.startswith('analysis_' + ts) and f.endswith('.md')]
    docs = {}
    for fname in sorted(files):
        doc = fname.replace('analysis_' + ts + '_', '').replace('.md', '')
        path = os.path.join(dirpath, fname)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        vals = parse_llm_table(content)
        docs[doc] = {'vals': vals, 'empty': is_empty_result(vals)}
    return docs


# ─── ОТЧЁТ ────────────────────────────────────────────────────

def report(m_map: dict, g_map: dict):
    common = sorted(set(m_map.keys()) & set(g_map.keys()))

    # Глобальные счётчики
    field_stats = {f: {'agree':0,'close':0,'differ':0,'empty':0,
                        'scores':[], 'm_vals':[], 'g_vals':[]}
                   for f in FIELDS}

    doc_scores = []   # итоговый score по документу

    per_doc = []

    for doc in common:
        mv = m_map[doc]['vals']
        gv = g_map[doc]['vals']

        doc_field_scores = []
        doc_result = {'doc': doc, 'fields': {}}

        for field in FIELDS:
            a = mv.get(field, '—')
            b = gv.get(field, '—')
            sc = semantic_sim(a, b)
            lb = label(sc, a, b)

            field_stats[field]['scores'].append(sc if lb != 'EMPTY' else None)
            field_stats[field]['m_vals'].append(a)
            field_stats[field]['g_vals'].append(b)
            if   lb == '✅ AGREE': field_stats[field]['agree']  += 1
            elif lb == '🟡 CLOSE': field_stats[field]['close']  += 1
            elif lb == '❌ DIFFER': field_stats[field]['differ'] += 1
            else:                  field_stats[field]['empty']  += 1

            if lb != 'EMPTY':
                doc_field_scores.append(
                    1.0 if lb=='✅ AGREE' else
                    0.5 if lb=='🟡 CLOSE' else 0.0
                )

            doc_result['fields'][field] = {
                'score': sc, 'label': lb, 'm': a, 'g': b
            }

        doc_score = sum(doc_field_scores)/len(doc_field_scores) if doc_field_scores else None
        doc_result['score'] = doc_score
        per_doc.append(doc_result)
        if doc_score is not None:
            doc_scores.append(doc_score)

    avg_doc_score = sum(doc_scores)/len(doc_scores) if doc_scores else 0

    # Подсчёт пустых
    m_empty = sum(1 for d in m_map.values() if d['empty'])
    g_empty = sum(1 for d in g_map.values() if d['empty'])

    # ─ Вывод ─
    sep = '='*72
    print(sep)
    print('CROSS-MODEL SCORER — ПАКЕТ 2 (2026-04-10_17-33-44)')
    print('Сравнение: Mistral 14B Reasoning vs Gemma 4-31B')
    print('Метод: Mistral-вывод ↔ Gemma-вывод (семантика без эталонов)')
    print(f'Пороги: AGREE≥{THRESH_HIGH}%  CLOSE≥{THRESH_MEDIUM}%  DIFFER<{THRESH_MEDIUM}%')
    print(sep)

    print(f"""
  ОБЩАЯ СТАТИСТИКА:
  {'Документов обработано':<40} {len(m_map):>8}  {len(g_map):>8}
  {'Пустых/None выводов':<40} {m_empty:>8}  {g_empty:>8}
  {'Документов с данными':<40} {len(m_map)-m_empty:>8}  {len(g_map)-g_empty:>8}
  {'Пар для сравнения (common)':<40} {len(common):>8}
  {'Средний % согласия (AGREE=1, CLOSE=0.5)':<40} {avg_doc_score:>7.1%}
""")

    # По полям
    print('СОГЛАСИЕ ПО ПОЛЯМ:')
    print(f"  {'Поле':<20} {'Avg%':>7} {'AGREE':>7} {'CLOSE':>7} {'DIFFER':>7} {'EMPTY':>7}")
    print('  ' + '-'*60)
    for field in FIELDS:
        st = field_stats[field]
        valid_scores = [s for s in st['scores'] if s is not None]
        avg = sum(valid_scores)/len(valid_scores) if valid_scores else 0
        print(f"  {FIELD_RU[field]:<20} {avg:>6.0f}%"
              f"  {st['agree']:>6}  {st['close']:>6}  {st['differ']:>6}  {st['empty']:>6}")

    # Детальный попарный разбор — лучшие совпадения
    print('\nДОКУМЕНТЫ С ВЫСОКИМ СОГЛАСИЕМ (score ≥ 75%):')
    hi_docs = sorted([d for d in per_doc if (d['score'] or 0) >= 0.75],
                     key=lambda d: d['score'], reverse=True)
    for d in hi_docs[:15]:
        print(f"  {d['score']:>5.0%}  {d['doc'][:62]}")

    print('\nДОКУМЕНТЫ С НИЗКИМ СОГЛАСИЕМ (score < 40%) — модели расходятся:')
    lo_docs = sorted([d for d in per_doc if d['score'] is not None and d['score'] < 0.40],
                     key=lambda d: d['score'])
    for d in lo_docs[:15]:
        print(f"  {d['score']:>5.0%}  {d['doc'][:62]}")

    # Самые спорные поля — примеры расхождений
    print('\nПРИМЕРЫ РАСХОЖДЕНИЙ (❌ DIFFER):')
    print('-'*72)
    shown = 0
    for d in per_doc:
        if shown >= 8: break
        for field in FIELDS:
            fdata = d['fields'].get(field, {})
            if fdata.get('label') == '❌ DIFFER':
                mv = fdata.get('m','')[:70]
                gv = fdata.get('g','')[:70]
                sc = fdata.get('score', 0)
                print(f"  [{sc:.0f}%] {d['doc'][:35]:35s} / {FIELD_RU[field]}")
                print(f"    Mistral: {mv}")
                print(f"    Gemma:   {gv}")
                shown += 1
                break

    # Итоговый вывод
    print('\n' + sep)
    print('ИТОГ:')
    total_agree  = sum(st['agree']  for st in field_stats.values())
    total_close  = sum(st['close']  for st in field_stats.values())
    total_differ = sum(st['differ'] for st in field_stats.values())
    total_empty  = sum(st['empty']  for st in field_stats.values())
    grand        = total_agree + total_close + total_differ + total_empty
    print(f"  ✅ AGREE  (≥85%): {total_agree:>4}  {total_agree/grand:.0%}")
    print(f"  🟡 CLOSE  (≥60%): {total_close:>4}  {total_close/grand:.0%}")
    print(f"  ❌ DIFFER (<60%): {total_differ:>4}  {total_differ/grand:.0%}")
    print(f"  ⬜ EMPTY:          {total_empty:>4}  {total_empty/grand:.0%}")
    print(f"\n  Средний % согласия: {avg_doc_score:.1%}")
    if avg_doc_score >= 0.70:
        verdict = "Модели ХОРОШО согласуются — можно доверять либо одной"
    elif avg_doc_score >= 0.50:
        verdict = "Модели ЧАСТИЧНО согласуются — гибридный подход оправдан"
    else:
        verdict = "Модели РАСХОДЯТСЯ — нужны эталоны для определения победителя"
    print(f"  Вердикт: {verdict}")
    print(sep)


if __name__ == '__main__':
    print(f'\nЗагрузка Пакет 2 Mistral ({MDIR})...')
    m_map = load_dir(MDIR, TS)
    print(f'Загрузка Пакет 2 Gemma ({GDIR})...')
    g_map = load_dir(GDIR, TS)
    print(f'  Mistral: {len(m_map)} файлов')
    print(f'  Gemma:   {len(g_map)} файлов\n')
    report(m_map, g_map)
