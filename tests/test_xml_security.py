import pytest
from pathlib import Path
from web_app_v6_cot_fallback import DocumentAnalyzer

def test_analyze_xml_vulnerability(tmp_path):
    analyzer = DocumentAnalyzer()
    xml_file = tmp_path / "test.xml"
    # Simple XML to check if it still works with defusedxml
    xml_file.write_text("<root><child>test</child></root>", encoding="utf-8")

    result = analyzer.analyze_xml(xml_file)
    assert 'error' not in result
    assert "test" in result['raw_text']
