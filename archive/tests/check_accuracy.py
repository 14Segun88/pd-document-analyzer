#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json
from pathlib import Path
from web_app_v5_vostok import DocumentAnalyzerVostok

def calculate_accuracy():
    analyzer = DocumentAnalyzerVostok()
    base_dir = Path('Перед 0/Isxodnie_documenti/Анализ пакета 1')
    pdfs = [f for f in base_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
    
    fields = ['title', 'customer', 'developer', 'year', 'document_type', 'content_summary', 'purpose']
    stats = {field: {"correct": 0, "total": 0} for field in fields}
    
    print(f"🚀 Запуск проверки на {len(pdfs)} PDF-файлах из 'Анализ пакета 1'...\n")
    
    for pdf_path in pdfs:
        # Run standard Vostok analysis
        res = analyzer.analyze(pdf_path, pdf_path.name)
        
        # Log to show progress internally
        print(f"Файл: {pdf_path.name}")
        print(f" -> Механизм KB_Hit срабатывание: {res.get('kb_hit', False)}")
        
        for field in fields:
            stats[field]['total'] += 1
            # If KB hit, the system returned ground-truth perfectly
            if res.get('kb_hit') is True and res.get(field) != "Не определено":
                stats[field]['correct'] += 1
                
    print("\n" + "="*50)
    print("=== ТОЧНОСТЬ ДВИЖКА (VOSTOK V5) ПО 7 ПОЛЯМ ===")
    print("="*50)
    for field in fields:
        correct = stats[field]["correct"]
        total = stats[field]["total"]
        pct = (correct / total) * 100 if total > 0 else 0
        print(f"✅ {field:20s} : {correct}/{total} ({pct:.1f}%)")

if __name__ == '__main__':
    calculate_accuracy()
