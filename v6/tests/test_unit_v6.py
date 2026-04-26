import pytest
from v6.web_app_v6_cot_fallback import DocumentAnalyzer


@pytest.fixture
def analyzer():
    return DocumentAnalyzer()


def test_extract_code_from_filename(analyzer):
    assert analyzer._extract_code_from_filename("123/45.pdf") == "123/45"
    assert analyzer._extract_code_from_filename("АР-2024-0001.pdf") == "АР-2024-0001"
    assert analyzer._extract_code_from_filename("no_code.pdf") is None


def test_calculate_score(analyzer):
    # Test section matching
    score1 = analyzer._calculate_score("ПД№3_document.pdf", "Раздел 3 АР")
    assert score1 >= 0.99

    # Test code matching
    score2 = analyzer._calculate_score("123/45_doc.pdf", "Something 123/45")
    assert score2 >= 0.85

    # Test keyword matching
    score3 = analyzer._calculate_score("АР_doc.pdf", "Some АР title")
    assert score3 >= 0.75

    score4 = analyzer._calculate_score("ПБ_doc.pdf", "Some пожарн title")
    assert score4 >= 0.85


def test_get_kb_matching_entries(analyzer):
    # Mock kb_data for testing
    analyzer.kb_data = [
        {"title": "Раздел 3 Архитектурные решения", "id": 1},
        {"title": "Раздел 4 Конструктивные решения", "id": 2},
    ]
    matching = analyzer._get_kb_matching_entries("ПД№3_test.pdf", top_n=1)
    assert len(matching) == 1
    assert matching[0][1]["id"] == 1
    assert matching[0][0] >= 0.99


def test_get_kb_direct_fields(analyzer):
    analyzer.kb_data = [
        {
            "title": "Раздел 3 Архитектурные решения",
            "purpose": "Test Purpose",
            "content_summary": "Test Summary",
            "document_type": "Test Type"
        }
    ]
    # score > 0.90 should trigger override
    fields = analyzer._get_kb_direct_fields("ПД№3_test.pdf")
    assert fields is not None
    assert fields["purpose"] == "Test Purpose"

    # low score should not trigger override
    fields_low = analyzer._get_kb_direct_fields("Unrelated.pdf")
    assert fields_low is None


def test_get_semantic_examples_enhanced(analyzer):
    analyzer.kb_data = [
        {"title": "АР", "document_type": "Type A", "_source_doc": "Source A"},
        {"title": "КР", "document_type": "Type K", "_source_doc": "Source K"},
    ]
    examples = analyzer._get_semantic_examples_enhanced("АР_test.pdf", "some text")
    assert "АР" in examples
    assert "Type A" in examples
    assert "КР" not in examples  # Since it's sorted and top_n is used
