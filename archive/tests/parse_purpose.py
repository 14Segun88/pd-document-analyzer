import sys
from docx import Document
from pathlib import Path
import json

files = [
    '/home/segun/CascadeProjects/Перед 0_2/Перед 0/Isxodnie_documenti/Образец_1.docx',
    '/home/segun/CascadeProjects/Перед 0_2/Перед 0/12 правильных ответов/Правильные ответы/Проверка для Георгия.docx',
    '/home/segun/CascadeProjects/Перед 0_2/Перед 0/12 правильных ответов/Правильные ответы/Проверка для Георгия_2.docx',
    '/home/segun/CascadeProjects/Перед 0_2/Перед 0/Isxodnie_documenti/Анализ пакета 1/Анализ Пакета_1.docx'
]

purposes = []

for file in files:
    try:
        doc = Document(file)
        for table in doc.tables:
            title = ""
            purpose_text = ""
            for row in table.rows:
                cells = row.cells
                if len(cells) >= 2:
                    k = cells[0].text.strip().lower()
                    v = cells[1].text.strip()
                    if k == 'название':
                        title = v
                    elif 'цель' in k:
                        purpose_text = v
            if title and purpose_text:
                purposes.append({'file': Path(file).name, 'title': title, 'purpose': purpose_text})
    except Exception as e:
        print(f"Failed {file}: {e}")

print(json.dumps(purposes, indent=2, ensure_ascii=False))
