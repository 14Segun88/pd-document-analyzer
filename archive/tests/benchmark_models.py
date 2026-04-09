import os
import sys
import glob
import time
import json
from pathlib import Path

# Добавляем путь к обновленному анализатору
sys.path.insert(0, str(Path('./.kilo/worktrees/playful-flower').absolute()))
try:
    from web_app_v6_cot_fallback import DocumentAnalyzer
except ImportError as e:
    print(f"Ошибка импорта DocumentAnalyzer: {e}")
    sys.exit(1)

def find_documents():
    paths = [
        "Перед 0/Isxodnie_documenti/**/*.*",
        "Перед 0/12 правильных ответов/Реальные документы/**/*.*",
        "Перед 0/12 правильных ответов/Скан/**/*.*"
    ]
    files = []
    for p in paths:
        files.extend(glob.glob(p, recursive=True))
    
    valid_extensions = {".pdf", ".xml", ".doc", ".docx"}
    docs = []
    for f in sorted(set(files), key=lambda x: os.path.basename(x)): # set to remove duplicates with stable sort
        ext = os.path.splitext(f)[1].lower()
        if ext not in valid_extensions:
            continue
        
        fname = os.path.basename(f)
        
        # Пропускаем файлы с ответами и служебные
        if "Анализ Пакета" in fname or fname.startswith("~$"):
            continue
        if "Проверка для Георгия" in fname:
            continue
        if "Образец_" in fname or "Запуск" in fname:
            continue
            
        docs.append(Path(f))
        
    return docs

def benchmark():
    docs = find_documents()
    print(f"Найдено документов для бенчмарка: {len(docs)}\n")
    
    analyzer = DocumentAnalyzer()
    
    target_keys = ['title', 'customer', 'developer', 'year', 'document_type', 'content_summary']
    
    total_files = len(docs)
    success_files = 0
    total_time = 0
    total_keys_found = 0
    expected_keys = total_files * len(target_keys)
    
    error_log_path = "ocr_errors.log"
    if os.path.exists(error_log_path):
        os.remove(error_log_path)
    
    for idx, doc_path in enumerate(docs, 1):
        start_time = time.time()
        
        try:
            ext = doc_path.suffix.lower()
            if ext == '.pdf':
                res = analyzer.analyze_pdf(doc_path)
            elif ext in ['.docx', '.doc']:
                res = analyzer.analyze_docx(doc_path)
            elif ext == '.xml':
                res = analyzer.analyze_xml(doc_path)
            else:
                continue
                
            error_msg = res.get('error', None)
            if error_msg:
                # Логируем ошибки OLMOCR отдельно
                with open(error_log_path, "a", encoding="utf-8") as erf:
                    erf.write(f"[{doc_path.name}] Error: {error_msg}\n")
            
            missing_keys = []
            found_count = 0
            
            for k in target_keys:
                val = res.get(k)
                if not val or val in ['—', 'неизвестно', ''] or "Error" in str(val):
                    missing_keys.append(k)
                else:
                    found_count += 1
            
            total_keys_found += found_count
            duration = round(time.time() - start_time, 1)
            total_time += duration
            
            if found_count == len(target_keys):
                success_files += 1
            
            fmt_str = res.get('format', 'UNKNOWN')
            
            missing_str = ", ".join(missing_keys) if missing_keys else ""
            status_symbol = "[x]" if missing_keys else "[v]"
            
            print(f"{idx}/{total_files} [{doc_path.name}] {fmt_str} - {found_count}/{len(target_keys)} keys, {status_symbol} Not found: [{missing_str}], {duration}s")
            
        except Exception as e:
            duration = round(time.time() - start_time, 1)
            print(f"{idx}/{total_files} [{doc_path.name}] ERROR - 0/6 keys, [x] Exception: {str(e)}, {duration}s")
            with open(error_log_path, "a", encoding="utf-8") as erf:
                erf.write(f"[{doc_path.name}] CRITICAL ERROR: {str(e)}\n")
                
    accuracy = (total_keys_found / expected_keys) * 100 if expected_keys > 0 else 0
    print("\n" + "="*50)
    print("Итоги бенчмарка:")
    print(f"Всего файлов: {total_files}")
    print(f"Файлов со 100% извлечением (все {len(target_keys)} ключей): {success_files}/{total_files}")
    print(f"Точность ключей: {total_keys_found}/{expected_keys} ({accuracy:.1f}%)")
    print(f"Общее время: {total_time:.1f}s (в среднем {total_time/total_files if total_files else 0:.1f} s/файл)")
    
    if os.path.exists(error_log_path):
        with open(error_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                print(f"Найдено ошибок ({len(lines)}). См. {error_log_path}")

if __name__ == "__main__":
    benchmark()
