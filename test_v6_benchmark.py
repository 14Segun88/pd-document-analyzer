#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Бенчмарк V6 на документах из Анализ пакета 1"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/home/segun/CascadeProjects/Перед 0_2/.kilo/worktrees/playful-flower')

from web_app_v6_cot_fallback import DocumentAnalyzer

def test_v6_on_documents():
    """Тестирование V6 на всех документах"""
    
    analyzer = DocumentAnalyzer()
    
    # Директория с документами
    base_dir = Path("/home/segun/CascadeProjects/Перед 0_2/Перед 0/Isxodnie_documenti/Анализ пакета 1")
    
    # Находим все PDF файлы
    pdf_files = list(base_dir.glob("*.pdf"))
    
    print(f"{'='*80}")
    print(f"V6 BENCHMARK - {len(pdf_files)} документов")
    print(f"{'='*80}")
    print()
    
    results = []
    total_fields = 0
    filled_fields = 0
    total_time = 0
    
    for pdf_file in pdf_files:
        print(f"\n{'─'*80}")
        print(f"📄 {pdf_file.name}")
        print(f"{'─'*80}")
        
        start_time = time.time()
        
        try:
            result = analyzer.analyze_pdf(pdf_file, pdf_file.name)
            elapsed = time.time() - start_time
            total_time += elapsed
            
            # Считаем заполненные поля
            fields = ['title', 'customer', 'developer', 'year', 'document_type', 'content_summary', 'purpose']
            doc_filled = 0
            doc_total = len(fields)
            
            print(f"⏱️  Время: {elapsed:.1f} сек")
            print(f"📊 Результаты:")
            
            for field in fields:
                value = result.get(field)
                total_fields += 1
                
                if value:
                    filled_fields += 1
                    doc_filled += 1
                    status = '✅'
                    # Обрезаем длинные значения
                    display_value = str(value)[:60] + '...' if len(str(value)) > 60 else str(value)
                else:
                    status = '❌'
                    display_value = 'Не извлечено'
                
                print(f"  {status} {field:20s}: {display_value}")
            
            accuracy = (doc_filled / doc_total) * 100
            print(f"\n📈 Точность документа: {accuracy:.0f}% ({doc_filled}/{doc_total})")
            
            results.append({
                'filename': pdf_file.name,
                'accuracy': accuracy,
                'filled': doc_filled,
                'total': doc_total,
                'time': elapsed,
                'result': result
            })
            
        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")
            results.append({
                'filename': pdf_file.name,
                'error': str(e)
            })
    
    # Итоговая статистика
    print(f"\n{'='*80}")
    print(f"📊 ИТОГОВАЯ СТАТИСТИКА V6")
    print(f"{'='*80}")
    
    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]
    
    if successful:
        avg_accuracy = sum(r['accuracy'] for r in successful) / len(successful)
        avg_time = sum(r['time'] for r in successful) / len(successful)
        
        # Считаем документы с 100% извлечением
        perfect_docs = [r for r in successful if r['accuracy'] == 100]
        good_docs = [r for r in successful if r['accuracy'] >= 70]
        
        print(f"\n✅ Успешно обработано: {len(successful)}/{len(results)}")
        print(f"❌ Ошибок: {len(failed)}")
        print()
        print(f"📊 Средняя точность: {avg_accuracy:.1f}%")
        print(f"📊 Поля заполнены: {filled_fields}/{total_fields} ({(filled_fields/total_fields)*100:.1f}%)")
        print(f"⏱️  Среднее время: {avg_time:.1f} сек")
        print(f"🎯 100% извлечение: {len(perfect_docs)}/{len(successful)} ({(len(perfect_docs)/len(successful))*100:.0f}%)")
        print(f"✨ ≥70% извлечение: {len(good_docs)}/{len(successful)} ({(len(good_docs)/len(successful))*100:.0f}%)")
        
        # Топ результатов
        print(f"\n🏆 ТОП-3 лучших результата:")
        sorted_results = sorted(successful, key=lambda x: x['accuracy'], reverse=True)
        for i, r in enumerate(sorted_results[:3], 1):
            print(f"  {i}. {r['filename'][:50]:50s} - {r['accuracy']:.0f}%")
        
        # Худшие результаты
        if len(successful) > 3:
            print(f"\n⚠️  Худшие результаты:")
            for r in sorted_results[-3:]:
                print(f"  - {r['filename'][:50]:50s} - {r['accuracy']:.0f}%")
    
    # Сохраняем результаты
    output_file = Path("/home/segun/CascadeProjects/Перед 0_2/v6_benchmark_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_documents': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'avg_accuracy': avg_accuracy if successful else 0,
            'avg_time': avg_time if successful else 0,
            'total_fields': total_fields,
            'filled_fields': filled_fields,
            'perfect_docs': len(perfect_docs) if successful else 0,
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Результаты сохранены: {output_file}")
    
    return results

if __name__ == '__main__':
    test_v6_on_documents()
