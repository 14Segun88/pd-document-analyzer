import pytest
import os
import sys
from pathlib import Path

# Add root directory to sys.path to import v6
sys.path.append(str(Path(__file__).parent.parent.parent))

from v6.web_app_v6_cot_fallback import DocumentAnalyzer

@pytest.fixture
def analyzer():
    return DocumentAnalyzer()

def test_extract_code_from_filename(analyzer):
    # Test typical construction document codes
    assert analyzer._extract_code_from_filename("157/25-АР.pdf") == "157/25"
    assert analyzer._extract_code_from_filename("157_25-АР.pdf") == "157/25"
    assert analyzer._extract_code_from_filename("МЕС-БМК-04/24-АР.pdf") == "МЕС-БМК-04/24"
    assert analyzer._extract_code_from_filename("NoCode.pdf") is None

def test_calculate_score(analyzer):
    # Test KB matching logic
    filename = "МЕС-БМК-04/24-АР.pdf"
    kb_title = "Раздел 3 Архитектурные решения (МЕС-БМК-04/24-АР)"

    score = analyzer._calculate_score(filename, kb_title)
    assert score >= 0.85  # Should be high due to code match

    score_low = analyzer._calculate_score("random.pdf", "Something Else")
    assert score_low < 0.5

def test_init_result(analyzer):
    res = analyzer._init_result("test.pdf", "pdf")
    assert res["filename"] == "test.pdf"
    assert "customer" in res
    assert "year" in res

def test_kb_matching_entries(analyzer):
    # Assuming knowledge_base.json exists and has some entries
    if not os.path.exists("knowledge_base.json"):
        pytest.skip("knowledge_base.json not found")

    entries = analyzer._get_kb_matching_entries("МЕС-БМК-04/24-АР.pdf", top_n=1)
    assert len(entries) <= 1
    if entries:
        score, entry = entries[0]
        assert isinstance(score, float)
        assert "title" in entry
