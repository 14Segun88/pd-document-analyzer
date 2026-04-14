import pytest
from pathlib import Path
import sys
import os

# Добавляем путь к v6 в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "v6"))

from web_app_v6_cot_fallback import DocumentAnalyzer

@pytest.fixture
def analyzer():
    return DocumentAnalyzer()

def test_extract_code_from_filename(analyzer):
    assert analyzer._extract_code_from_filename("157/25-ПЗ") == "157/25"
    assert analyzer._extract_code_from_filename("Шифр: 1234/2024") == "1234/2024"
    assert analyzer._extract_code_from_filename("ПЗ-2023-4567") == "ПЗ-2023-4567"
    assert analyzer._extract_code_from_filename("обычный файл.pdf") is None

def test_calculate_score(analyzer):
    # ПД№
    score = analyzer._calculate_score("ПД№3_АР.pdf", "Раздел 3 Архитектурные решения")
    assert score >= 0.99

    # Шифр
    score = analyzer._calculate_score("157/25-АР.pdf", "Пояснительная записка 157/25")
    assert score >= 0.85

    # Ключевые слова
    score = analyzer._calculate_score("АР_проект.pdf", "Архитектурные решения")
    assert score >= 0.75

def test_init_result(analyzer):
    res = analyzer._init_result("test.pdf", "PDF")
    assert res['filename'] == "test.pdf"
    assert res['format'] == "PDF"
    assert all(k in res for k in ['title', 'customer', 'developer', 'year', 'document_type', 'content_summary', 'purpose', 'raw_text'])
