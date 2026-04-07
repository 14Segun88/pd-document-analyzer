#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json
from pathlib import Path

from web_app_v5_vostok import DocumentAnalyzerVostok

def main():
    analyzer = DocumentAnalyzerVostok()
    base_dir = Path('Перед 0/Isxodnie_documenti/Анализ пакета 1')
    all_files = [f for f in base_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.pdf', '.xml', '.docx']]
    
    print(f"🚀 Запускаем анализ {len(all_files)} файлов в 'Анализ пакета 1' через Vostok...")
    for file_path in all_files:
        print(f"\n{'='*70}\n📄 ФАЙЛ: {file_path.name}\n{'='*70}")
        if not file_path.exists():
            print("Файл не найден!")
            continue
            
        res = analyzer.analyze(file_path, file_path.name)
        
        # Оставляем нужные ключи + kb_hit
        keys_to_print = ['title', 'customer', 'developer', 'year', 'document_type', 'content_summary', 'purpose', 'kb_hit']
        clean_res = {k: res.get(k) for k in keys_to_print}
        
        print(json.dumps(clean_res, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
