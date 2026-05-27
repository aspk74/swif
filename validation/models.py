"""
Pydantic models for the telemetry validation pipeline.

- TelemetryPayload: incoming device telemetry events.
- ComplianceViolation: recorded when telemetry deviates from a rule.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import random


class RemediationAction(str, Enum):
    """The action the system took in response to a violation."""
    LOGGED_FOR_REVIEW = "LOGGED_FOR_REVIEW"
    AUTOMATED_FIX = "AUTOMATED_FIX"
    QUARANTINED = "QUARANTINED"
    GRACE_PERIOD = "GRACE_PERIOD"


class TelemetryPayload(BaseModel):
    """Schema for incoming device telemetry events."""
    device_id: str = Field(description="Unique identifier for the reporting device")
    device_name: Optional[str] = Field(default="Unknown Device", description="Human-readable device name")
    os_type: Optional[str] = Field(default=None, description="Operating system type (e.g., android, ios, chrome)")
    technical_parameter: str = Field(description="The setting/parameter being reported")
    value: str = Field(description="The current value observed on the device")
    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the telemetry was captured. Defaults to server receive time."
    )

    @field_validator("os_type", mode="before")
    @classmethod
    def validate_os_type(cls, v):
        if not v or str(v).strip().lower() in ("unknown", "unknown device", "none", "null", ""):
            return random.choice(["android", "ios", "chrome"])
        os_lower = str(v).strip().lower()
        if "android" in os_lower:
            return "android"
        if "ios" in os_lower or "iphone" in os_lower or "ipad" in os_lower:
            return "ios"
        if "chrome" in os_lower or "chromium" in os_lower:
            return "chrome"
        if "mac" in os_lower or "apple" in os_lower:
            return "ios"
        if "win" in os_lower:
            return "android"
        if "linux" in os_lower:
            return "chrome"
        return random.choice(["android", "ios", "chrome"])


class ComplianceViolation(BaseModel):
    """A recorded compliance violation event persisted to MongoDB."""
    device_id: str
    device_name: str = "Unknown Device"
    os_type: str = "chrome"
    rule_id: str = Field(description="The content-hash rule_id from the rules registry")
    suggested_id: str = Field(description="Human-readable rule identifier (e.g., AC-1.1)")
    technical_parameter: str
    expected_value: str
    actual_value: str
    logic_operator: str = Field(description="The LogicOperator that was evaluated")
    severity: str
    action_taken: RemediationAction = Field(
        default=RemediationAction.LOGGED_FOR_REVIEW,
        description="What the system did in response to this violation"
    )
    remediation_command: Optional[str] = Field(
        default=None,
        description="The resolved remediation command or description"
    )
    remediation_logs: Optional[str] = Field(
        default=None,
        description="Simulation execution output of the self-healing or quarantine action"
    )
    remediation_timestamp: Optional[datetime] = Field(
        default=None,
        description="When the remediation action was executed"
    )
    violated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    grace_period_expires_at: Optional[datetime] = Field(
        default=None,
        description="When the grace period expires and the violation escalates"
    )

    @field_validator("os_type", mode="before")
    @classmethod
    def validate_os_type(cls, v):
        if not v or str(v).strip().lower() in ("unknown", "unknown device", "none", "null", ""):
            return random.choice(["android", "ios", "chrome"])
        os_lower = str(v).strip().lower()
        if "android" in os_lower:
            return "android"
        if "ios" in os_lower or "iphone" in os_lower or "ipad" in os_lower:
            return "ios"
        if "chrome" in os_lower or "chromium" in os_lower:
            return "chrome"
        if "mac" in os_lower or "apple" in os_lower:
            return "ios"
        if "win" in os_lower:
            return "android"
        if "linux" in os_lower:
            return "chrome"
        return random.choice(["android", "ios", "chrome"])
