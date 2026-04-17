import pytest
from v6.web_app_v6_cot_fallback import DocumentAnalyzer


@pytest.fixture
def analyzer():
    return DocumentAnalyzer()


def test_scoring_PD_number(analyzer):
    # Test matching by PD number
    filename = "Раздел_ПД№3_АР.pdf"
    kb_title = "Раздел 3 Архитектурные решения (157/25-АР)"
    score = analyzer._calculate_score(filename, kb_title)
    assert score >= 0.99


def test_scoring_abbreviation(analyzer):
    # Test matching by abbreviation
    filename = "Документ_АР.pdf"
    kb_title = "Архитектурные решения (АР)"
    score = analyzer._calculate_score(filename, kb_title)
    assert score >= 0.75


def test_extract_code(analyzer):
    assert analyzer._extract_code_from_filename("157/25-АР") == "157/25"
    assert analyzer._extract_code_from_filename("АР-2024-0001") == "АР-2024-0001"


def test_kb_direct_fields(analyzer):
    # Mock kb_data to ensure predictable test results
    analyzer.kb_data = [
        {
            "title": "Раздел 3 Архитектурные решения",
            "purpose": "Test Purpose",
            "content_summary": "Test Summary",
            "document_type": "АР"
        }
    ]

    fields = analyzer._get_kb_direct_fields("Раздел_ПД№3_АР.pdf")
    assert fields is not None
    assert fields['document_type'] == "АР"
