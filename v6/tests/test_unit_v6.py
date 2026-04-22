import pytest
from v6.web_app_v6_cot_fallback import DocumentAnalyzer
from unittest.mock import MagicMock, patch


@pytest.fixture
def analyzer():
    return DocumentAnalyzer()


def test_extract_code_from_filename(analyzer):
    # Test year-style code
    assert analyzer._extract_code_from_filename("1234/5678") == "1234/5678"
    # Test Russian-style project code
    assert (analyzer._extract_code_from_filename("АР-2024-0001") ==
            "АР-2024-0001")
    # Test no match
    assert analyzer._extract_code_from_filename("random_file.pdf") is None


def test_calculate_score(analyzer):
    # Test section match boost
    score = analyzer._calculate_score("ПД№3_something.pdf",
                                      "Раздел 3 Architecture")
    assert score >= 0.99

    # Test code match boost
    score = analyzer._calculate_score("157/25-АР.pdf",
                                      "Раздел 3 АР (157/25-АР)")
    assert score >= 0.85

    # Test keyword match boost (e.g., АР)
    score = analyzer._calculate_score("АР_doc.pdf", "АР project")
    assert score >= 0.75


@patch('requests.post')
def test_call_llm_success(mock_post, analyzer):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'choices': [{
            'message': {
                'content': '{"title": "Test Title", "customer": "Test Customer", "developer": "Test Dev", "year": "2025", "document_type": "Test Type", "content_summary": "Test Summary", "purpose": "Test Purpose"}'  # noqa: E501
            }
        }]
    }
    mock_post.return_value = mock_response

    result = analyzer._call_llm("sample text", "test_file.pdf")

    assert result is not None
    assert result['title'] == "Test Title"
    assert result['customer'] == "Test Customer"


def test_init_result(analyzer):
    result = analyzer._init_result("test.pdf", "PDF")
    assert result['filename'] == "test.pdf"
    assert result['format'] == "PDF"
    fields = ['title', 'customer', 'developer', 'year', 'document_type',
              'content_summary', 'purpose']
    assert all(k in result for k in fields)
