import pytest
import os
import sys
from pathlib import Path

# Add the root directory to sys.path to import v6
sys.path.insert(0, str(Path(__file__).parent.parent.parent.absolute()))

from v6.web_app_v6_cot_fallback import DocumentAnalyzer

@pytest.fixture
def analyzer():
    return DocumentAnalyzer()

def test_extract_code_from_filename(analyzer):
    assert analyzer._extract_code_from_filename("157/25-АР") == "157/25"
    assert analyzer._extract_code_from_filename("АР-2024-1234") == "АР-2024-1234"
    assert analyzer._extract_code_from_filename("no_code_here") is None

def test_calculate_score_exact_match(analyzer):
    # Testing direct match via SequenceMatcher and section boost
    score = analyzer._calculate_score("ПД№3_АР.pdf", "Раздел 3 АР")
    assert score >= 0.99

def test_calculate_score_code_match(analyzer):
    # Testing match via code extraction
    score = analyzer._calculate_score("157/25-АР.pdf", "Документ 157/25")
    assert score >= 0.85

def test_calculate_score_keyword_boost(analyzer):
    # Testing keyword boosts
    assert analyzer._calculate_score("something_АР.pdf", "Another АР") >= 0.75
    assert analyzer._calculate_score("something_КР.pdf", "Another КР") >= 0.75
    assert analyzer._calculate_score("something_ПБ.pdf", "пожарная безопасность") >= 0.85

def test_init_result(analyzer):
    result = analyzer._init_result("test.pdf", "PDF")
    assert result['filename'] == "test.pdf"
    assert result['format'] == "PDF"
    assert result['title'] is None
    assert "raw_text" in result

def test_get_kb_matching_entries(analyzer):
    # If KB is loaded, it should return some entries
    if analyzer.kb_data:
        entries = analyzer._get_kb_matching_entries("АР.pdf", top_n=1)
        assert len(entries) <= 1
        if entries:
            assert isinstance(entries[0][0], float) # score
            assert isinstance(entries[0][1], dict) # entry

def test_get_semantic_examples_enhanced(analyzer):
    examples = analyzer._get_semantic_examples_enhanced("test.pdf", "some document text")
    assert isinstance(examples, str)
    if analyzer.kb_data:
        assert "ПРИМЕР" in examples
    else:
        assert "ПРИМЕРЫ НЕ ДОСТУПНЫ" in examples
