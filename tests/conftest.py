import pytest
import mongomock
from unittest.mock import patch
from db.storage import RuleStore
from pipeline.ingestion import Chunk

@pytest.fixture
def store():
    # RuleStore now natively supports mongomock:// scheme for testing
    store = RuleStore(uri="mongomock://localhost", db_name="compliance_db", collection_name="rules")
    yield store

@pytest.fixture
def sample_chunk():
    return Chunk(
        title="4.1 Password Policy",
        text="All passwords must be at least 14 characters long and contain special characters.",
        start_page=4,
        end_page=4
    )

@pytest.fixture
def sample_llm_output():
    return [
        {
            "suggested_id": "AC-1.1",
            "category": "Access Control",
            "technical_parameter": "password_min_length",
            "expected_value": "14",
            "logic": "GREATER_THAN_OR_EQUAL",
            "severity": "HIGH"
        }
    ]

@pytest.fixture
def invalid_llm_output():
    return [
        {
            "suggested_id": "AC-1.1",
            # Missing category
            "technical_parameter": "password_min_length",
            "expected_value": "14",
            "logic": "INVALID_LOGIC", # Invalid enum
            "severity": "HIGH"
        }
    ]
