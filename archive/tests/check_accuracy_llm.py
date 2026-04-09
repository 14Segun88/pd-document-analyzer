#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json
from pathlib import Path
from web_app_v5_vostok import DocumentAnalyzerVostok

def is_match(ai, gt):
    if not ai or ai == "Не определено": return False
    a = ai.lower()
    g = gt.lower()
    if a == g: return True
    if len(a) > 5 and a in g: return True
    if len(g) > 5 and g in a: return True
    
    # Check for heavy overlap (>70%)
    a_words = set(a.replace('"', '').replace('«','').replace('»','').split())
    g_words = set(g.replace('"', '').replace('«','').replace('»','').split())
    if not a_words or not g_words: return False
    
    overlap = len(a_words.intersection(g_words))
    if overlap / len(g_words) >= 0.7 or overlap / len(a_words) >= 0.7:
        return True
        
    return False

def calculate_accuracy():
    analyzer = DocumentAnalyzerVostok()
    base_dir = Path('Перед 0/Isxodnie_documenti/Анализ пакета 1')
    pdfs = [f for f in base_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
    
    fields = ['title', 'customer', 'developer', 'year', 'document_type', 'content_summary', 'purpose']
    stats = {field: {"correct": 0, "total": 0} for field in fields}
    
    print(f"🚀 Запуск проверки на {len(pdfs)} PDF-файлах через Mistral 14B...\n")
    
    for pdf_path in pdfs:
        # Read text
        ext = pdf_path.suffix.lower()
        import fitz
        doc = fitz.open(pdf_path)
        text = "\\n".join(p.get_text() for p in doc)
        doc.close()
        
        # Get ground truth
        ground_truth = analyzer._get_semantic_match(pdf_path.name, text)
        if not ground_truth:
            print(f"Файл: {pdf_path.name} -> ОШИБКА: Нет эталона в KB для проверки!")
            continue
            
        print(f"Файл: {pdf_path.name}")
        print("  -> Ожидание ответа от LLM...")
        
        # Call LLM directly to avoid regex fixups or KB fallbacks muddying the test
        ai_data = analyzer._call_llm(text, pdf_path.name)
        
        # If the LLM throws an error or returns empty
        if not ai_data:
            print("  -> ОШИБКА: LLM не вернул данные (Timeout или сервер недоступен).")
            for field in fields:
                stats[field]['total'] += 1
            continue
            
        all_correct = True
        for field in fields:
            stats[field]['total'] += 1
            
            ai_val = str(ai_data.get(field, "")).strip()
            gt_val = str(ground_truth.get(field, "")).strip()
            
            if is_match(ai_val, gt_val):
                stats[field]['correct'] += 1
            else:
                all_correct = False
                print(f"    [X] {field}:")
                # print snippet to avoid console flooding
                print(f"        AI : {ai_val[:120]}")
                print(f"        KB : {gt_val[:120]}")
                
        if all_correct:
            print("  -> 100% совпадение генерации LLM для этого файла!\n")
        else:
            print("\n")
                
    print("="*50)
    print("=== ТОЧНОСТЬ MISTRAL 14B ПО 7 ПОЛЯМ ===")
    print("="*50)
    for field in fields:
        correct = stats[field]["correct"]
        total = stats[field]["total"]
        pct = (correct / total) * 100 if total > 0 else 0
        print(f"{'✅' if pct == 100 else '⚠️'} {field:20s} : {correct}/{total} ({pct:.1f}%)")

if __name__ == '__main__':
    calculate_accuracy()
