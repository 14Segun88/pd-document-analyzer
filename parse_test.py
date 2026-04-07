import zipfile
import xml.etree.ElementTree as ET

def extract_tables_from_docx(path):
    with zipfile.ZipFile(path) as docx:
        tree = ET.XML(docx.read('word/document.xml'))
        tables = []
        for tbl in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl'):
            table_data = []
            for tr in tbl.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'):
                row_data = []
                for tc in tr.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
                    texts = [node.text for node in tc.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
                    row_data.append(''.join(texts).strip())
                table_data.append(row_data)
            tables.append(table_data)
        return tables

print(extract_tables_from_docx("Перед 0/12 правильных ответов/Правильные ответы/Проверка для Георгия.docx"))
