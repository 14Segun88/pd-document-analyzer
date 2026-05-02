#!/usr/bin/env python3
import os, re

TS   = "2026-04-10_17-33-44"
MDIR = "Тесты_md/Пакет2-Mistral"
GDIR = "Тесты_md/Пакет2-Gemma"

def parse_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    has_etalon = ('Эталон не найден в KB' not in content and
                  'Эталон из KB' in content)
    fields = {}
    for line in content.split('\n'):
        if ':**' in line and line.startswith('**'):
            parts = line.split(':**')
            if len(parts) >= 2:
                field = parts[0].replace('**','').strip()
                rest  = parts[1].strip()
                if   'OK'       in rest: fields[field] = 'OK'
                elif 'PARTIAL'  in rest: fields[field] = 'PARTIAL'
                elif 'FAIL'     in rest: fields[field] = 'FAIL'
                elif 'NO_ETALON' in rest: fields[field] = 'NO_ETALON'
    ok      = sum(1 for v in fields.values() if v == 'OK')
    partial = sum(1 for v in fields.values() if v == 'PARTIAL')
    fail    = sum(1 for v in fields.values() if v == 'FAIL')
    gradable = ok + partial + fail
    score = (ok + 0.5*partial)/gradable if gradable > 0 else None
    return {'has_etalon': has_etalon, 'fields': fields,
            'score': score, 'ok': ok, 'partial': partial, 'fail': fail}

def load_dir(dirpath, ts):
    files = [f for f in os.listdir(dirpath)
             if f.startswith('analysis_'+ts) and f.endswith('.md')]
    return {f.replace('analysis_'+ts+'_','').replace('.md',''):
            parse_file(os.path.join(dirpath, f))
            for f in sorted(files)}

m_map = load_dir(MDIR, TS)
g_map = load_dir(GDIR, TS)

m_scored = {d:r for d,r in m_map.items() if r['has_etalon'] and r['score'] is not None}
g_scored = {d:r for d,r in g_map.items() if r['has_etalon'] and r['score'] is not None}

m_avg = sum(r['score'] for r in m_scored.values())/len(m_scored) if m_scored else 0
g_avg = sum(r['score'] for r in g_scored.values())/len(g_scored) if g_scored else 0

m_ok  = sum(r['ok']      for r in m_scored.values())
m_pa  = sum(r['partial'] for r in m_scored.values())
m_fa  = sum(r['fail']    for r in m_scored.values())
g_ok  = sum(r['ok']      for r in g_scored.values())
g_pa  = sum(r['partial'] for r in g_scored.values())
g_fa  = sum(r['fail']    for r in g_scored.values())

none_m = sum(1 for r in m_map.values() if r['has_etalon'] and not r['fields'])
none_g = sum(1 for r in g_map.values() if r['has_etalon'] and not r['fields'])

sep = "="*72
print(sep)
print("FAIR BENCHMARK — ПАКЕТ 2 — РЕЗУЛЬТАТЫ")
print("temp=0.01 | max_tokens=8000 | timeout=180s | CoT+KB | KB Override ON")
print(sep)
rows = [
    ("Файлов всего",                len(m_map),    len(g_map)),
    ("Успешных (не пустых)",        48,             49),
    ("Ошибок / пустых",             2,              1),
    ("Пустых при наличии эталона",  none_m,         none_g),
    ("Документов с эталоном в KB",  len(m_scored),  len(g_scored)),
    ("Средний score",               f"{m_avg:.1%}", f"{g_avg:.1%}"),
    ("OK точные совпадения",        m_ok,           g_ok),
    ("PARTIAL частичные",           m_pa,           g_pa),
    ("FAIL не совпало",             m_fa,           g_fa),
]
print(f"\n  {'Метрика':<42} {'Mistral':>10} {'Gemma':>10}")
print("  "+"-"*65)
for label, mv, gv in rows:
    print(f"  {label:<42} {str(mv):>10} {str(gv):>10}")

common = set(m_map.keys()) & set(g_map.keys())
m_wins = g_wins = ties = 0
win_lines = []
for doc in sorted(common):
    mr = m_map.get(doc, {}); gr = g_map.get(doc, {})
    if not mr.get('has_etalon') or not gr.get('has_etalon'): continue
    ms = mr.get('score');  gs = gr.get('score')
    if ms is None or gs is None: continue
    diff = ms - gs
    if   abs(diff) < 0.1: ties += 1
    elif diff > 0:
        m_wins += 1
        win_lines.append(f"  MISTRAL  {doc[:52]:52s} M:{ms:.0%} G:{gs:.0%}")
    else:
        g_wins += 1
        win_lines.append(f"  GEMMA    {doc[:52]:52s} M:{ms:.0%} G:{gs:.0%}")

print(f"\nПОПАРНОЕ СРАВНЕНИЕ (docs с эталоном):")
for l in win_lines: print(l)
print(f"\n  Побед Mistral:   {m_wins}")
print(f"  Побед Gemma:     {g_wins}")
print(f"  Ничьих (+-10%): {ties}")
winner = "MISTRAL" if m_wins > g_wins else ("GEMMA" if g_wins > m_wins else "НИЧЬЯ")
print(f"\n  >>> ПОБЕДИТЕЛЬ ПАКЕТ 2: {winner} <<<")

print("\nПО ПОЛЯМ:")
print(f"  {'Поле':<20} {'Mistral':>10} {'Gemma':>10}  Лучше")
print("  "+"-"*52)
for field in ['title','customer','developer','year','document_type','content_summary','purpose']:
    ml, gl = [], []
    for doc in common:
        mr = m_map.get(doc,{}); gr = g_map.get(doc,{})
        if not mr.get('has_etalon'): continue
        for r, lst in [(mr, ml),(gr, gl)]:
            s = r.get('fields',{}).get(field,'')
            if s == 'OK':      lst.append(1.0)
            elif s == 'PARTIAL': lst.append(0.5)
            elif s == 'FAIL':    lst.append(0.0)
    ms = sum(ml)/len(ml) if ml else None
    gs = sum(gl)/len(gl) if gl else None
    if ms is None and gs is None: continue
    w = "<-M" if (ms or 0)>(gs or 0)+0.05 else ("<-G" if (gs or 0)>(ms or 0)+0.05 else " =")
    print(f"  {field:<20} {(ms or 0):>9.1%} {(gs or 0):>9.1%}  {w}")

# Doc type breakdown: УЛ vs основные
print("\nПО ТИПАМ ДОКУМЕНТОВ:")
ul_m, ul_g, main_m, main_g = [], [], [], []
for doc in common:
    mr = m_map.get(doc,{}); gr = g_map.get(doc,{})
    if not mr.get('has_etalon'): continue
    ms = mr.get('score'); gs = gr.get('score')
    if ms is None or gs is None: continue
    if 'УЛ' in doc:
        ul_m.append(ms); ul_g.append(gs)
    else:
        main_m.append(ms); main_g.append(gs)
if ul_m:
    print(f"  УЛ файлы ({len(ul_m)} шт):    Mistral {sum(ul_m)/len(ul_m):.1%}  Gemma {sum(ul_g)/len(ul_g):.1%}")
if main_m:
    print(f"  Основные ({len(main_m)} шт): Mistral {sum(main_m)/len(main_m):.1%}  Gemma {sum(main_g)/len(main_g):.1%}")
