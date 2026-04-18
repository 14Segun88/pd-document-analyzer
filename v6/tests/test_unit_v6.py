import pytest
from v6.web_app_v6_cot_fallback import DocumentAnalyzer


@pytest.fixture
def analyzer():
    return DocumentAnalyzer()


def test_extract_code_from_filename(analyzer):
    assert analyzer._extract_code_from_filename("157/25-АР") == "157/25"
    assert analyzer._extract_code_from_filename("АР-2024-001") == "АР-2024-001"
    assert analyzer._extract_code_from_filename("no_code_here") is None


def test_calculate_score(analyzer):
    # Test section matching
    assert analyzer._calculate_score(
        "ПД№3_something",
        "Раздел 3 Архитектурные решения"
    ) >= 0.99

    # Test code matching
    assert analyzer._calculate_score(
        "157/25-АР.pdf",
        "Раздел 4 (157/25-КР)"
    ) >= 0.85

    # Test keyword matching
    assert analyzer._calculate_score(
        "АР_doc.pdf",
        "Раздел 3 АР"
    ) >= 0.75
    assert analyzer._calculate_score(
        "ПБ_doc.pdf",
        "Мероприятия по пожарной безопасности"
    ) >= 0.85


def test_init_result(analyzer):
    result = analyzer._init_result("test.pdf", "PDF")
    assert result["filename"] == "test.pdf"
    assert result["format"] == "PDF"
    assert all(k in result for k in ["title", "customer", "developer", "year",
                                     "document_type", "content_summary",
                                     "purpose"])


def test_kb_loading(analyzer):
    # Should at least be a list
    assert isinstance(analyzer.kb_data, list)
