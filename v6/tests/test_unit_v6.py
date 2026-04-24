import pytest
from v6.web_app_v6_cot_fallback import DocumentAnalyzer
from unittest.mock import patch, MagicMock

@pytest.fixture
def analyzer():
    return DocumentAnalyzer()

def test_extract_code_from_filename(analyzer):
    assert analyzer._extract_code_from_filename("157/25-АР") == "157/25"
    assert analyzer._extract_code_from_filename("АР-2024-1234") == "АР-2024-1234"
    assert analyzer._extract_code_from_filename("unknown") is None

def test_calculate_score(analyzer):
    # Perfect match on section number
    assert analyzer._calculate_score("ПД№3_something.pdf", "Раздел 3 ПЗ") >= 0.99

    # Matching codes
    assert analyzer._calculate_score("157/25-АР.pdf", "Раздел 3 АР (157/25-АР)") >= 0.85

    # Industry abbreviations
    assert analyzer._calculate_score("АР_document.pdf", "Something with АР") >= 0.75

def test_kb_matching_entries(analyzer):
    # Mock kb_data
    analyzer.kb_data = [
        {"title": "Раздел 3 Архитектурные решения (157/25-АР)", "purpose": "Testing"},
        {"title": "Раздел 4 Конструктивные решения (157/25-КР)", "purpose": "Testing"}
    ]
    matches = analyzer._get_kb_matching_entries("157/25-АР.pdf")
    assert len(matches) > 0
    assert "АР" in matches[0][1]["title"]

@patch('requests.post')
def test_call_llm_failure(mock_post, analyzer):
    mock_post.return_value.status_code = 500
    result = analyzer._call_llm("some text", "test.pdf")
    assert result is None

@patch('requests.post')
def test_call_llm_success(mock_post, analyzer):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'choices': [{
            'message': {
                'content': '{"title": "Test Doc", "customer": "Test Cust", "developer": "Test Dev", "year": "2025", "document_type": "PZ", "content_summary": "Sum", "purpose": "Goal"}'
            }
        }]
    }
    mock_post.return_value = mock_response

    result = analyzer._call_llm("some text", "test.pdf")
    assert result is not None
    assert result['title'] == "Test Doc"
