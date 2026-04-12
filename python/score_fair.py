#!/usr/bin/env python3
import os, re

TIMESTAMP = "2026-04-09_22-50-30"

def parse_file(path):
    with open(path,'r',encoding='utf-8') as f:
        content = f.read()
    has_etalon = ('**Эталон не найден в KB**' not in content and 
                  '## Эталон из KB' in content)
    fields = {}
    for line in content.split('\n'):
        m = re.match(r'\*\*(\w+)\*\*:\s*(✅ OK|🟡 PARTIAL|❌ FAIL|⬜ NO_ETALON)', line)
        if m:
            fields[m.group(1)] = m.group(2)
    ok = sum(1 for v in fields.values() if '✅' in v)
    partial = sum(1 for v in fields.values() if '🟡' in v)
    fail = sum(1 for v in fields.values() if '❌' in v)
    gradable = ok + partial + fail
    score = (ok + 0.5*partial)/gradable if gradable > 0 else None
    return {'has_etalon': has_etalon, 'fields': fields, 'score': score,
            'ok': ok, 'partial': partial, 'fail': fail}

def analyze_dir(dirpath, timestamp):
    files = [f for f in os.listdir(dirpath) 
             if f.startswith('analysis_'+timestamp) and f.endswith('.md')]
    per_doc = {}
    for fname in sorted(files):
        doc = fname.replace('analysis_'+timestamp+'_','').replace('.md','')
        r = parse_file(os.path.join(dirpath, fname))
        per_doc[doc] = r
    return per_doc

m_map = analyze_dir('Тесты_md', TIMESTAMP)
g_map = analyze_dir('Тесты_md/Тесты_md2-Gemma', TIMESTAMP)

m_scored = {d:r for d,r in m_map.items() if r['has_etalon'] and r['score'] is not None}
g_scored = {d:r for d,r in g_map.items() if r['has_etalon'] and r['score'] is not None}

m_avg = sum(r['score'] for r in m_scored.values())/len(m_scored) if m_scored else 0
g_avg = sum(r['score'] for r in g_scored.values())/len(g_scored) if g_scored else 0

sep = "="*70
print(sep)
print("FAIR BENCHMARK — РЕЗУЛЬТАТЫ (одинаковые условия V6)")
print("temp=0.01 | max_tokens=8000 | timeout=180s | CoT+KB | KB Override ON")
print(sep)

none_m = sum(1 for r in m_map.values() if r['has_etalon'] and not r['fields'])
none_g = sum(1 for r in g_map.values() if r['has_etalon'] and not r['fields'])

sum_ok_m  = sum(r['ok']      for r in m_scored.values())
sum_pa_m  = sum(r['partial'] for r in m_scored.values())
sum_fa_m  = sum(r['fail']    for r in m_scored.values())
sum_ok_g  = sum(r['ok']      for r in g_scored.values())
sum_pa_g  = sum(r['partial'] for r in g_scored.values())
sum_fa_g  = sum(r['fail']    for r in g_scored.values())

rows = [
    ("Файлов всего",                    len(m_map),    len(g_map)),
    ("Пустых/None выводов",             none_m,        none_g),
    ("Документов с эталоном",           len(m_scored), len(g_scored)),
    ("Средний score",                   f"{m_avg:.1%}", f"{g_avg:.1%}"),
    ("OK точное совпадение",            sum_ok_m,      sum_ok_g),
    ("PARTIAL частичное",               sum_pa_m,      sum_pa_g),
    ("FAIL не совпало",                 sum_fa_m,      sum_fa_g),
]
print(f"\n  {'Метрика':<42} {'Mistral':>10} {'Gemma':>10}")
print("  "+"-"*64)
for label, mv, gv in rows:
    print(f"  {label:<42} {str(mv):>10} {str(gv):>10}")

common = set(m_map.keys()) & set(g_map.keys())
print("\nПОПАРНОЕ (только docs с эталоном):")
m_wins = g_wins = ties = 0
lines = []
for doc in sorted(common):
    mr = m_map.get(doc,{}); gr = g_map.get(doc,{})
    if not mr.get('has_etalon') or not gr.get('has_etalon'): continue
    ms = mr.get('score'); gs = gr.get('score')
    if ms is None or gs is None: continue
    diff = ms - gs
    if abs(diff) < 0.1: ties += 1
    elif diff > 0:
        m_wins += 1
        lines.append(f"  MISTRAL  {doc[:50]:50s} M:{ms:.0%} G:{gs:.0%}")
    else:
        g_wins += 1
        lines.append(f"  GEMMA    {doc[:50]:50s} M:{ms:.0%} G:{gs:.0%}")
for l in lines: print(l)
print(f"\n  Побед Mistral:  {m_wins}")
print(f"  Побед Gemma:    {g_wins}")
print(f"  Ничьих (+-10%): {ties}")

print("\nПО ПОЛЯМ:")
print(f"  {'Поле':<20} {'Mistral':>10} {'Gemma':>10}  Лучше")
print("  "+"-"*50)
for field in ['title','customer','developer','year','document_type','content_summary','purpose']:
    ms_list = []; gs_list = []
    for doc in common:
        mr = m_map.get(doc,{}); gr = g_map.get(doc,{})
        if not mr.get('has_etalon'): continue
        for r, lst in [(mr,ms_list),(gr,gs_list)]:
            s = r.get('fields',{}).get(field,'')
            if '✅' in s: lst.append(1.0)
            elif '🟡' in s: lst.append(0.5)
            elif '❌' in s: lst.append(0.0)
    ms = sum(ms_list)/len(ms_list) if ms_list else None
    gs = sum(gs_list)/len(gs_list) if gs_list else None
    if ms is None and gs is None: continue
    winner = "<-M" if (ms or 0)>(gs or 0)+0.05 else ("<-G" if (gs or 0)>(ms or 0)+0.05 else " =")
    print(f"  {field:<20} {(ms or 0):>9.1%} {(gs or 0):>9.1%}  {winner}")
