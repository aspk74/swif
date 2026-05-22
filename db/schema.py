from pydantic import BaseModel, Field, AliasChoices, ConfigDict
from enum import Enum
from typing import Optional
from datetime import datetime, timezone

class LogicOperator(str, Enum):
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    REGEX_MATCH = "REGEX_MATCH"
    EXISTS = "EXISTS"
    NOT_EXISTS = "NOT_EXISTS"

class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"

class LLMExtractionResult(BaseModel):
    """The raw structure we expect the LLM to return."""
    model_config = ConfigDict(extra='allow')
    suggested_id: str = Field(
        validation_alias=AliasChoices("suggested_id", "suggest_id", "id"),
        description="A suggested human-readable identifier for the rule (e.g., AC-1.1)"
    )
    category: str = Field(description="The security category, e.g., 'Access Control', 'Network Security'")
    technical_parameter: str = Field(
        validation_alias=AliasChoices("technical_parameter", "parameter", "setting"),
        description="The technical setting or parameter this rule enforces"
    )
    expected_value: str = Field(
        validation_alias=AliasChoices("expected_value", "value", "expected"),
        description="The target value. Always a string; deterministic validator will cast it based on the logic operator"
    )
    logic: LogicOperator = Field(description="The logic operator to use when validating the technical parameter")
    severity: SeverityLevel = Field(
        validation_alias=AliasChoices("severity", "severity_level"),
        description="The severity level if this rule is violated"
    )

class SecurityRule(BaseModel):
    """The full database document structure."""
    model_config = ConfigDict(extra='allow')
    rule_id: str = Field(description="Deterministically generated content hash for deduplication")
    suggested_id: str
    category: str
    technical_parameter: str
    expected_value: str
    logic: LogicOperator
    severity: SeverityLevel
    source_document: str = Field(description="The filename of the source policy")
    chunk_reference: str = Field(description="Reference to the section in the PDF where this rule was found")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
