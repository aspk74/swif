import json
from unittest.mock import patch, MagicMock
from pipeline.extractor import GeminiExtractor, generate_rule_id
from db.schema import SecurityRule

def test_generate_rule_id():
    id1 = generate_rule_id("Access Control", "min_length", "14")
    id2 = generate_rule_id("Access Control", "min_length", "14")
    id3 = generate_rule_id("Access Control", "min_length", "15")
    
    assert id1 == id2 # Deterministic
    assert id1 != id3 # Collision resistant

@patch('pipeline.extractor.call_gemini_api')
def test_extract_rules_success(mock_call, sample_chunk, sample_llm_output):
    mock_call.side_effect = [
        json.dumps(sample_llm_output),
        json.dumps([True])
    ]
    
    extractor = GeminiExtractor(api_key="dummy")
    
    # We mock time.sleep to avoid waiting during tests
    with patch('time.sleep', return_value=None):
        rules = extractor.extract_rules(sample_chunk, "doc.pdf")
        
    assert len(rules) == 1
    assert isinstance(rules[0], SecurityRule)
    assert rules[0].technical_parameter == "password_min_length"
    assert rules[0].source_document == "doc.pdf"

@patch('pipeline.extractor.call_gemini_api')
def test_extract_rules_repair_loop(mock_call, sample_chunk, invalid_llm_output, sample_llm_output):
    # First call returns invalid JSON, second call returns valid JSON, third is verification
    mock_call.side_effect = [
        json.dumps(invalid_llm_output),
        json.dumps(sample_llm_output),
        json.dumps([True])
    ]
    
    extractor = GeminiExtractor(api_key="dummy")
    
    with patch('time.sleep', return_value=None):
        rules = extractor.extract_rules(sample_chunk, "doc.pdf")
        
    assert len(rules) == 1
    assert mock_call.call_count == 3


@patch('pipeline.extractor.call_gemini_api')
def test_extract_rules_with_dynamic_attributes(mock_call, sample_chunk):
    # Mock return value containing standard fields and extra dynamic fields, and verification
    mock_call.side_effect = [
        json.dumps([
            {
                "suggested_id": "AC-1.1",
                "category": "Access Control",
                "technical_parameter": "password_min_length",
                "expected_value": "14",
                "logic": "GREATER_THAN_OR_EQUAL",
                "severity": "HIGH",
                "remediation": "Update security settings.",
                "tags": ["password", "auth"]
            }
        ]),
        json.dumps([True])
    ]
    
    extractor = GeminiExtractor(api_key="dummy")
    
    with patch('time.sleep', return_value=None):
        rules = extractor.extract_rules(sample_chunk, "doc.pdf")
        
    assert len(rules) == 1
    assert isinstance(rules[0], SecurityRule)
    # Check standard attributes
    assert rules[0].technical_parameter == "password_min_length"
    # Check extra dynamic attributes
    assert rules[0].model_extra["remediation"] == "Update security settings."
    assert rules[0].model_extra["tags"] == ["password", "auth"]

