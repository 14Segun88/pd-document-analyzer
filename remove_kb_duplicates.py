#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для удаления дубликатов из knowledge_base.json
"""

import json
from pathlib import Path

def main():
    kb_path = Path(__file__).parent / "knowledge_base.json"
    
    with open(kb_path, 'r', encoding='utf-8') as f:
        kb_data = json.load(f)
    
    print(f"Исходное количество записей: {len(kb_data)}")
    
    # Группируем по title
    seen = {}
    duplicates = []
    
    for i, entry in enumerate(kb_data):
        title = entry.get('title', '')
        # Нормализуем title для сравнения
        key = title.split('(')[0].strip() if '(' in title else title
        
        if key in seen:
            duplicates.append((i, title, seen[key]))
        else:
            seen[key] = (i, title)
    
    print(f"\nНайдено дубликатов: {len(duplicates)}")
    
    for dup_idx, dup_title, (orig_idx, orig_title) in duplicates:
        print(f"\nДубликат #{dup_idx}: {dup_title[:70]}")
        print(f"  Оригинал #{orig_idx}: {orig_title[:70]}")
    
    # Удаляем дубликаты
    unique_kb = []
    seen_keys = set()
    
    for entry in kb_data:
        title = entry.get('title', '')
        key = title.split('(')[0].strip() if '(' in title else title
        
        if key not in seen_keys:
            unique_kb.append(entry)
            seen_keys.add(key)
    
    print(f"\nПосле удаления дубликатов: {len(unique_kb)} записей")
    
    # Сохраняем
    backup_path = kb_path.parent / "knowledge_base_backup.json"
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(kb_data, f, ensure_ascii=False, indent=2)
    print(f"Резервная копия: {backup_path}")
    
    with open(kb_path, 'w', encoding='utf-8') as f:
        json.dump(unique_kb, f, ensure_ascii=False, indent=2)
    print(f"Обновлённый KB: {kb_path}")

if __name__ == '__main__':
    main()
