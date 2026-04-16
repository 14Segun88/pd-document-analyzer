import pytest
from v6.web_app_v6_cot_fallback import DocumentAnalyzer

@pytest.fixture
def analyzer():
    return DocumentAnalyzer()

def test_extract_code_from_filename(analyzer):
    # Test year format /25
    assert analyzer._extract_code_from_filename("ПД№4 МЕС-БМК-04/24-КР.pdf") == "04/24"
    # Test longer code format
    assert analyzer._extract_code_from_filename("АР-2023-1234.pdf") == "АР-2023-1234"
    # Test no code
    assert analyzer._extract_code_from_filename("random_file.pdf") is None

def test_calculate_score(analyzer):
    # Test high score for section match
    score = analyzer._calculate_score("ПД№4.pdf", "Раздел 4 Архитектурные решения")
    assert score >= 0.99

    # Test high score for industry abbreviation
    score = analyzer._calculate_score("Project-АР.pdf", "Чертежи АР")
    assert score >= 0.75

    # Test low score for unrelated
    score = analyzer._calculate_score("random.pdf", "Something else")
    assert score < 0.5
