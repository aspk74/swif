from db.schema import SecurityRule
from db.storage import RuleStore

def test_upsert_rule(store: RuleStore):
    rule = SecurityRule(
        rule_id="hash-123",
        suggested_id="ID-1",
        category="Test",
        technical_parameter="param",
        expected_value="val",
        logic="EQUALS",
        severity="LOW",
        source_document="doc.pdf",
        chunk_reference="chunk 1"
    )
    
    # First insert
    is_new = store.upsert_rule(rule)
    assert is_new is True
    assert store.collection.count_documents({}) == 1
    
    # Upsert same rule (duplicate)
    is_new = store.upsert_rule(rule)
    assert is_new is False
    assert store.collection.count_documents({}) == 1

def test_upsert_rules_batch(store: RuleStore):
    rule1 = SecurityRule(
        rule_id="hash-1", suggested_id="ID-1", category="C1",
        technical_parameter="p1", expected_value="v1", logic="EQUALS",
        severity="LOW", source_document="doc.pdf", chunk_reference="1"
    )
    rule2 = SecurityRule(
        rule_id="hash-2", suggested_id="ID-2", category="C2",
        technical_parameter="p2", expected_value="v2", logic="EQUALS",
        severity="LOW", source_document="doc.pdf", chunk_reference="2"
    )
    # Duplicate of rule1
    rule1_dup = SecurityRule(
        rule_id="hash-1", suggested_id="ID-1-DUP", category="C1",
        technical_parameter="p1", expected_value="v1", logic="EQUALS",
        severity="LOW", source_document="doc.pdf", chunk_reference="1"
    )
    
    stats = store.upsert_rules_batch([rule1, rule2, rule1_dup])
    
    assert stats["inserted"] == 2
    assert stats["duplicates_in_batch"] == 1
    assert store.collection.count_documents({}) == 2


def test_get_all_rules_deduplication(store: RuleStore):
    # Two similar rules in the same category, checking the same expected value/logic,
    # but slightly different technical parameters (System vs Library folder)
    rule1 = SecurityRule(
        rule_id="hash-system",
        suggested_id="5.1.7",
        category="File System Security",
        technical_parameter="World Writable Files in System Folder",
        expected_value="No World Writable Files",
        logic="EQUALS",
        severity="CRITICAL",
        source_document="doc.pdf",
        chunk_reference="chunk 1"
    )
    rule2 = SecurityRule(
        rule_id="hash-library",
        suggested_id="5.1.8",
        category="File System Security",
        technical_parameter="World Writable Files in Library Folder",
        expected_value="No World Writable Files",
        logic="EQUALS",
        severity="CRITICAL",
        source_document="doc.pdf",
        chunk_reference="chunk 1"
    )
    # A completely distinct rule in the same category
    rule3 = SecurityRule(
        rule_id="hash-distinct",
        suggested_id="5.1.9",
        category="File System Security",
        technical_parameter="Root Login Disabled",
        expected_value="Disabled",
        logic="EQUALS",
        severity="HIGH",
        source_document="doc.pdf",
        chunk_reference="chunk 1"
    )
    
    # Insert all three
    store.upsert_rule(rule1)
    store.upsert_rule(rule2)
    store.upsert_rule(rule3)
    
    assert store.collection.count_documents({}) == 3
    
    # Fetch without deduplication
    all_rules = store.get_all_rules(unique=False)
    assert len(all_rules) == 3
    
    # Fetch with deduplication (default)
    unique_rules = store.get_all_rules(unique=True, similarity_threshold=0.8)
    # rule1 and rule2 are similar (approx 82% similarity) and should deduplicate to 1
    # rule3 is distinct and should be kept
    # Total unique rules should be 2
    assert len(unique_rules) == 2


def test_dynamic_attributes_storage(store: RuleStore):
    # Test that extra attributes are permitted and saved/loaded properly
    rule = SecurityRule(
        rule_id="hash-dynamic",
        suggested_id="5.1.10",
        category="Dynamic Security",
        technical_parameter="Dynamic Param",
        expected_value="Value",
        logic="EQUALS",
        severity="MEDIUM",
        source_document="doc.pdf",
        chunk_reference="chunk 1",
        # Extra custom attributes not declared in original SecurityRule schema
        remediation="Ensure this is configured.",
        tags=["dynamic", "compliance"]
    )
    
    store.upsert_rule(rule)
    
    # Read back from database
    db_rule = store.get_rule("hash-dynamic")
    assert db_rule is not None
    assert db_rule["remediation"] == "Ensure this is configured."
    assert db_rule["tags"] == ["dynamic", "compliance"]
    
    # Convert back to SecurityRule model and check extra fields
    loaded_rule = SecurityRule(**db_rule)
    assert loaded_rule.model_extra["remediation"] == "Ensure this is configured."
    assert loaded_rule.model_extra["tags"] == ["dynamic", "compliance"]
