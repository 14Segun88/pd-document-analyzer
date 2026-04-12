#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
semantic_scorer_v2.py
Семантическое сравнение LLM-выводов с KB эталонами.

Подход: взят из web_app_v6_cot_fallback.py (_calculate_score)
+ rapidfuzz token_sort_ratio для устойчивости к перестановкам слов.

Входные данные: MD-файлы из fair benchmark (timestamp 2026-04-09_22-50-30)
Раздел "## Сравнение LLM vs Эталон" содержит строки:
    - LLM: <значение>
    - Эталон: <значение>
"""

import os, re
from difflib import SequenceMatcher
from rapidfuzz import fuzz

# ─── КОНФИГУРАЦИЯ ───────────────────────────────────────────────
TS   = "2026-04-09_22-50-30"
MDIR = "Тесты_md"
GDIR = "Тесты_md/Тесты_md2-Gemma"

# Пороги семантического совпадения (как в V6 KB matching)
THRESH_HIGH   = 85   # ✅ Высокое совпадение
THRESH_MEDIUM = 60   # 🟡 Частичное совпадение
# < 60           → ❌ Низкое

FIELDS = ['title', 'customer', 'developer', 'year',
          'document_type', 'content_summary', 'purpose']

# ─── СЕМАНТИЧЕСКАЯ ФУНКЦИЯ (из V6 cot_fallback) ─────────────────

def semantic_sim(llm_val: str, et_val: str) -> float:
    """
    Семантическое сходство 0–100, тот же подход что в V6:
      - SequenceMatcher (difflib) — базовый ratio
      - token_sort_ratio (rapidfuzz) — устойчив к порядку слов
      - WRatio (rapidfuzz) — взвешенное комбо
      - acronym bonus — за совпадающие аббревиатуры (ГКУ, ДЗКС...)
    """
    lv = (llm_val or '').strip()
    ev = (et_val  or '').strip()

    # Пустые или заглушки
    if not lv or not ev or lv.lower() in ('—','none','') or ev.lower() in ('—','none',''):
        return 0.0

    lv_low = lv.lower()
    ev_low = ev.lower()

    # 1. difflib SequenceMatcher (как в V6 _calculate_score)
    base = SequenceMatcher(None, lv_low, ev_low).ratio() * 100

    # 2. rapidfuzz — token_sort (слова в любом порядке)
    ts = fuzz.token_sort_ratio(lv_low, ev_low)

    # 3. rapidfuzz — partial (если одно содержит другое)
    pr = fuzz.partial_ratio(lv_low, ev_low)

    # 4. rapidfuzz — WRatio (взвешенное)
    wr = fuzz.WRatio(lv_low, ev_low)

    best = max(base, ts, pr, wr)

    # 5. Аббревиатурный бонус (как в V6: МЕС-БМК, ГКУ, ДЗКС...)
    acr_l = set(re.findall(r'[А-ЯA-Z]{2,}', lv))
    acr_e = set(re.findall(r'[А-ЯA-Z]{2,}', ev))
    shared_acr = acr_l & acr_e
    bonus = min(len(shared_acr) * 5, 15)

    # 6. Год-бонус: если оба содержат одинаковый год
    years_l = set(re.findall(r'\b(20\d{2})\b', lv))
    years_e = set(re.findall(r'\b(20\d{2})\b', ev))
    if years_l & years_e:
        bonus += 10

    return min(best + bonus, 100.0)


def label(score: float) -> str:
    if score >= THRESH_HIGH:   return '✅ HIGH'
    if score >= THRESH_MEDIUM: return '🟡 MED'
    return '❌ LOW'


# ─── ПАРСИНГ MD ФАЙЛОВ ─────────────────────────────────────────

def parse_comparison(content: str) -> dict:
    """
    Парсит раздел '## Сравнение LLM vs Эталон'.
    Возвращает {field: {'llm': ..., 'etalon': ...}}
    """
    idx = content.find('## Сравнение LLM vs Эталон')
    if idx == -1:
        return {}

    block = content[idx:]
    result = {}
    cur_field = None

    for line in block.split('\n'):
        # Строка вида: **fieldname:** STATUS
        if line.startswith('**') and ':**' in line:
            field = line.split(':**')[0].replace('**', '').strip()
            if field in FIELDS:
                cur_field = field
                result[cur_field] = {'llm': '', 'etalon': ''}

        elif cur_field:
            if line.startswith('- LLM:'):
                result[cur_field]['llm'] = line[len('- LLM:'):].strip()
            elif line.startswith('- Эталон:'):
                result[cur_field]['etalon'] = line[len('- Эталон:'):].strip()

    return result


def score_file(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    has_etalon = ('Эталон не найден в KB'   not in content and
                  'Эталон из KB'            in  content and
                  'Сравнение невозможно'    not in content)

    cmp = parse_comparison(content)

    per_field = {}
    for field in FIELDS:
        pair = cmp.get(field, {})
        lv = pair.get('llm',    '')
        ev = pair.get('etalon', '')
        if has_etalon and ev and ev.lower() not in ('—','none',''):
            sc = semantic_sim(lv, ev)
            lb = label(sc)
        else:
            sc = None
            lb = 'NO_ETALON'
        per_field[field] = {'score': sc, 'label': lb, 'llm': lv, 'etalon': ev}

    # Итоговый score документа (только по полям с эталоном)
    gradable = [(f, v) for f, v in per_field.items()
                if v['label'] in ('✅ HIGH','🟡 MED','❌ LOW')]
    if gradable:
        doc_score = sum(
            1.0 if v['label']=='✅ HIGH' else
            0.5 if v['label']=='🟡 MED'  else 0.0
            for _, v in gradable
        ) / len(gradable)
    else:
        doc_score = None

    return {'has_etalon': has_etalon, 'fields': per_field,
            'score': doc_score, 'n_fields': len(gradable)}


def load_dir(dirpath: str, ts: str) -> dict:
    files = [f for f in os.listdir(dirpath)
             if f.startswith('analysis_' + ts) and f.endswith('.md')]
    return {
        f.replace('analysis_'+ts+'_','').replace('.md',''):
        score_file(os.path.join(dirpath, f))
        for f in sorted(files)
    }


# ─── ОТЧЁТ ─────────────────────────────────────────────────────

def report(m_map: dict, g_map: dict):
    m_sc = {d:r for d,r in m_map.items() if r['has_etalon'] and r['score'] is not None}
    g_sc = {d:r for d,r in g_map.items() if r['has_etalon'] and r['score'] is not None}

    m_avg = sum(r['score'] for r in m_sc.values()) / len(m_sc) if m_sc else 0
    g_avg = sum(r['score'] for r in g_sc.values()) / len(g_sc) if g_sc else 0

    def tally(scored):
        hi=med=low=none=0
        for r in scored.values():
            for fv in r['fields'].values():
                lb = fv['label']
                if   lb=='✅ HIGH':   hi   += 1
                elif lb=='🟡 MED':   med  += 1
                elif lb=='❌ LOW':   low  += 1
                else:                 none += 1
        return hi, med, low, none

    mh,mm,ml,mn = tally(m_sc)
    gh,gm,gl,gn = tally(g_sc)

    sep = '='*72
    print(sep)
    print('SEMANTIC SCORER V2 — Пакет 1 (Fair benchmark 2026-04-09_22-50-30)')
    print(f'Метод: SequenceMatcher + rapidfuzz WRatio/token_sort + acronym/year bonus')
    print(f'Пороги: HIGH≥{THRESH_HIGH}%  MED≥{THRESH_MEDIUM}%  LOW<{THRESH_MEDIUM}%')
    print(sep)

    rows = [
        ('Документов с эталоном',           len(m_sc),       len(g_sc)),
        ('Средний score (HIGH=1, MED=0.5)', f'{m_avg:.1%}',  f'{g_avg:.1%}'),
        ('✅ HIGH  совпадение',              mh,              gh),
        ('🟡 MED   частичное',              mm,              gm),
        ('❌ LOW   не совпало',             ml,              gl),
        ('⬜ NO_ETALON',                    mn,              gn),
    ]
    print(f"\n  {'Метрика':<46} {'Mistral':>10} {'Gemma':>10}")
    print('  '+'-'*68)
    for lbl, mv, gv in rows:
        print(f"  {lbl:<46} {str(mv):>10} {str(gv):>10}")

    # Попарное сравнение
    common = set(m_map.keys()) & set(g_map.keys())
    mw=gw=ties=0
    win_lines=[]
    for doc in sorted(common):
        mr=m_map.get(doc,{}); gr=g_map.get(doc,{})
        if not mr.get('has_etalon') or not gr.get('has_etalon'): continue
        ms=mr.get('score');  gs=gr.get('score')
        if ms is None or gs is None: continue
        diff=ms-gs
        if   abs(diff)<0.08: ties+=1
        elif diff>0:
            mw+=1
            win_lines.append(f"  MISTRAL  {doc[:54]:54s} M:{ms:.0%} G:{gs:.0%}")
        else:
            gw+=1
            win_lines.append(f"  GEMMA    {doc[:54]:54s} M:{ms:.0%} G:{gs:.0%}")

    print(f"\nПОПАРНОЕ СРАВНЕНИЕ (docs с эталоном):")
    for l in win_lines: print(l)
    print(f"\n  Побед Mistral:   {mw}")
    print(f"  Побед Gemma:     {gw}")
    print(f"  Ничьих (±8%):   {ties}")
    winner = 'MISTRAL' if mw>gw else ('GEMMA' if gw>mw else 'НИЧЬЯ')
    print(f"\n  >>> ПОБЕДИТЕЛЬ: {winner} <<<")

    # По полям — avg semantic score
    print(f"\nСЕМАНТИЧЕСКИЙ SCORE ПО ПОЛЯМ (среднее %, чем выше — тем лучше):")
    print(f"  {'Поле':<22} {'Mistral':>10} {'Gemma':>10}  Лучше")
    print('  '+'-'*54)
    for field in FIELDS:
        ml_s,gl_s=[],[]
        for doc in common:
            mr=m_map.get(doc,{}); gr=g_map.get(doc,{})
            if not mr.get('has_etalon'): continue
            mf=mr['fields'].get(field,{}); gf=gr['fields'].get(field,{})
            if mf.get('score') is not None: ml_s.append(mf['score'])
            if gf.get('score') is not None: gl_s.append(gf['score'])
        ms_a = sum(ml_s)/len(ml_s) if ml_s else None
        gs_a = sum(gl_s)/len(gl_s) if gl_s else None
        if ms_a is None and gs_a is None: continue
        w = '<-M' if (ms_a or 0)>(gs_a or 0)+3 else ('<-G' if (gs_a or 0)>(ms_a or 0)+3 else ' =')
        print(f"  {field:<22} {(ms_a or 0):>9.1f}% {(gs_a or 0):>9.1f}%  {w}")

    # Примеры: где семантика выявляет реальное качество
    print(f"\nПРИМЕРЫ — где семантика ЛУЧШЕ чем точное совпадение:")
    print('-'*72)
    shown = 0
    for doc in sorted(common):
        if shown >= 6: break
        mr = m_map.get(doc, {})
        if not mr.get('has_etalon'): continue
        for field, fdata in mr['fields'].items():
            lv = fdata.get('llm','')
            ev = fdata.get('etalon','')
            sc = fdata.get('score')
            lb = fdata.get('label','')
            if sc and sc >= 60 and sc < 98 and lv and ev and lv != ev:
                print(f"  [{lb} {sc:.0f}%] {doc[:30]:30s} / {field}")
                print(f"    LLM:    {lv[:80]}")
                print(f"    Эталон: {ev[:80]}")
                shown += 1
                break


if __name__ == '__main__':
    print(f"\nЗагрузка результатов (ts={TS})...")
    m_map = load_dir(MDIR, TS)
    g_map = load_dir(GDIR, TS)
    print(f"  Mistral: {len(m_map)} файлов")
    print(f"  Gemma:   {len(g_map)} файлов\n")
    report(m_map, g_map)
