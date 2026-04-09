import os
import glob
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

def extract_tables_from_docx(path):
    tables_data = []
    try:
        with zipfile.ZipFile(path) as docx:
            tree = ET.XML(docx.read('word/document.xml'))
            for tbl in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl'):
                table_dict = {}
                for tr in tbl.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'):
                    row_data = []
                    for tc in tr.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
                        texts = [node.text for node in tc.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
                        row_data.append(''.join(texts).strip())
                    
                    if len(row_data) >= 2:
                        key = row_data[0].strip()
                        val = row_data[1].strip()
                        # Mapping russian keys to our english DB structure
                        if 'Название' in key:
                            table_dict['title'] = val
                        elif 'Заказчик' in key:
                            table_dict['customer'] = val
                        elif 'Подрядчик' in key or 'проектная фирма' in key or 'Проектировщик' in key:
                            table_dict['developer'] = val
                        elif 'Год' in key:
                            table_dict['year'] = val
                        elif 'Тип' in key:
                            table_dict['document_type'] = val
                        elif 'Содержимое' in key:
                            table_dict['content_summary'] = val
                        elif 'Цель' in key:
                            table_dict['purpose'] = val
                
                required_keys = {'title', 'customer', 'developer', 'year', 'document_type', 'content_summary'}
                if table_dict and len(required_keys.intersection(table_dict.keys())) >= 4:
                    tables_data.append(table_dict)
    except Exception as e:
        print(f"Error parsing {path}: {e}")
    return tables_data

def main():
    kb_entries = []
    base_dir = Path(__file__).resolve().parent
    
    # 1. Gather docs from "12 правильных ответов/Правильные ответы"
    path_12 = str(base_dir / "Перед 0/12 правильных ответов/Правильные ответы/*.docx")
    
    # 2. Gather docs from "Isxodnie_documenti"
    path_isx = str(base_dir / "Перед 0/Isxodnie_documenti/**/*.docx")

    files = glob.glob(path_12) + glob.glob(path_isx, recursive=True)
    
    for f in files:
        if "Образец_" in f or "Запуск" in f:
            continue
            
        print(f"Processing: {f}")
        tables = extract_tables_from_docx(f)
        for t in tables:
            # Add metadata about source file if helpful
            t['_source_doc'] = os.path.basename(f)
            kb_entries.append(t)
            
    print(f"Total KB entries extracted: {len(kb_entries)}")
    
    with open("knowledge_base.json", "w", encoding="utf-8") as out:
        json.dump(kb_entries, out, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
