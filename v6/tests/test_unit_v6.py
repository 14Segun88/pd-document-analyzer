import pytest
import sys
from pathlib import Path
from typing import Dict, Any

# Add root to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from v6.web_app_v6_cot_fallback import DocumentAnalyzer


@pytest.fixture
def analyzer() -> DocumentAnalyzer:
    return DocumentAnalyzer()


def test_extract_code_from_filename(analyzer: DocumentAnalyzer) -> None:
    assert analyzer._extract_code_from_filename("157/25-АР") == "157/25"
    code = "ПД-2023-1234"
    assert analyzer._extract_code_from_filename(code) == "ПД-2023-1234"
    assert analyzer._extract_code_from_filename("no-code") is None


def test_calculate_score_exact_match(analyzer: DocumentAnalyzer) -> None:
    # ПД№3 should match Раздел 3
    score = analyzer._calculate_score("ПД№3.pdf", "Раздел 3 АР")
    assert score >= 0.99


def test_calculate_score_acronym(analyzer: DocumentAnalyzer) -> None:
    score = analyzer._calculate_score("file_AR.pdf", "Something АР")
    assert score >= 0.75


def test_kb_loading(analyzer: DocumentAnalyzer) -> None:
    # Depending on whether knowledge_base.json exists in root
    assert isinstance(analyzer.kb_data, list)


def test_init_result(analyzer: DocumentAnalyzer) -> None:
    res: Dict[str, Any] = analyzer._init_result("test.pdf", "PDF")
    assert res['filename'] == "test.pdf"
    assert res['format'] == "PDF"
    assert 'title' in res
    assert 'raw_text' in res
