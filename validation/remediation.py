"""
Tiered Remediation Layer for the SWIF compliance engine.

Implements the RemediationManager which evaluates violations and takes
graded actions (Review, Automated Fix, Quarantine) based on severity.
"""
import sys
import os
from datetime import datetime, timezone
from typing import Optional

# Add parent directory to path to ensure clean imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.logger import get_logger
from validation.models import ComplianceViolation, RemediationAction
from db.schema import SeverityLevel

logger = get_logger(__name__)


def quarantine_device(device_id: str, rule_id: str, suggested_id: str, parameter: str) -> str:
    """
    Simulates placing a device into network and identity quarantine.
    Prints a visually premium console warning and returns execution logs.
    """
    # Stylized ASCII quarantine banner
    banner = f"""
┌──────────────────────────────────────────────────────────┐
│         🚨  [CRITICAL VIOLATION - DEVICE ISOLATED]       │
├──────────────────────────────────────────────────────────┤
│ DEVICE ID:   {device_id:<43} │
│ RULE ID:     {rule_id:<43} │
│ SUGGESTED ID:{suggested_id:<43} │
│ PARAMETER:   {parameter:<43} │
├──────────────────────────────────────────────────────────┤
│ [SYSTEM ACTION] INITIATING SECURE ENCLAVE QUARANTINE...  │
│ [SYSTEM ACTION] Revoking Active Directory & IdP tokens...│
│ [SYSTEM ACTION] Blocking LAN & WAN access via network agent│
│ [SYSTEM ACTION] Pushing compliance-isolation profile...  │
│ [STATUS]       DEVICE SUCCESSFULLY QUARANTINED & SILENCED│
└──────────────────────────────────────────────────────────┘
"""
    print(banner, flush=True)
    
    logs = (
        f"[SYSTEM ACTION] Initiating quarantine sequence for {device_id} due to {suggested_id}.\n"
        "[SYSTEM ACTION] Revoking IdP tokens... Done.\n"
        "[SYSTEM ACTION] Disabling LAN & WAN access... Done.\n"
        "[SYSTEM ACTION] Pushing MDM isolation profile... Done.\n"
        f"[STATUS] Device {device_id} has been fully isolated in state: QUARANTINED."
    )
    return logs


class RemediationManager:
    """
    Evaluates compliance violations and executes tiered remediation:
    - Tier 1 (LOW/MEDIUM): Log and resolve command for human review.
    - Tier 2 (HIGH): Automated self-healing (simulated MDM execution).
    - Tier 3 (CRITICAL): Complete device isolation (quarantine).
    """

    def __init__(self):
        pass

    def evaluate_violation(
        self, device_id: str, rule: dict, actual_value: str,
        device_name: str = "Unknown Device", os_type: str = "Unknown"
    ) -> ComplianceViolation:
        """
        Grades the violation based on severity and takes the corresponding
        remediation action, returning an enriched ComplianceViolation model.
        """
        rule_id = rule.get("rule_id", "UNKNOWN")
        suggested_id = rule.get("suggested_id", "UNKNOWN")
        parameter = rule.get("technical_parameter", "UNKNOWN")
        expected_value = rule.get("expected_value", "UNKNOWN")
        logic = rule.get("logic", "EQUALS")
        
        # Raw severity from rule (default to MEDIUM)
        raw_severity = rule.get("severity", "MEDIUM")
        try:
            severity = SeverityLevel(raw_severity)
        except ValueError:
            severity = SeverityLevel.MEDIUM

        # Resolve remediation command with fallbacks
        remediation_command = rule.get("remediation_command_terminal")
        if not remediation_command:
            remediation_command = rule.get("remediation")
        if not remediation_command:
            remediation_command = f"sudo compliance-fix --parameter {parameter}"

        action_taken = RemediationAction.LOGGED_FOR_REVIEW
        remediation_logs: Optional[str] = None
        remediation_timestamp: Optional[datetime] = None

        grace_period_expires_at: Optional[datetime] = None

        if severity == SeverityLevel.LOW:
            # ── Tier 1a: Grace Period ─────────────────────────────────────────
            action_taken = RemediationAction.GRACE_PERIOD
            from datetime import timedelta
            grace_period_expires_at = datetime.now(timezone.utc) + timedelta(minutes=2)
            remediation_logs = (
                f"[SYSTEM NOTIFICATION] Device has entered a 2-minute grace period.\n"
                f"Suggested manual remediation: {remediation_command}"
            )
            logger.info(f"Tier 1a Remediation applied to {device_id}: Grace Period active.")

        elif severity == SeverityLevel.MEDIUM:
            # ── Tier 1b: Logged for Review ────────────────────────────────────
            action_taken = RemediationAction.LOGGED_FOR_REVIEW
            remediation_logs = (
                f"Manual operator review recommended.\n"
                f"Suggested manual remediation: {remediation_command}"
            )
            logger.info(f"Tier 1b Remediation applied to {device_id}: Logged for Review.")

        elif severity == SeverityLevel.HIGH:
            # ── Tier 2: Automated Self-Healing (MDM Simulation) ───────────────
            action_taken = RemediationAction.AUTOMATED_FIX
            remediation_timestamp = datetime.now(timezone.utc)
            
            # Stylized ASCII auto-fix console banner
            banner = f"""
┌──────────────────────────────────────────────────────────┐
│              🛠️  [MDM AUTOMATED SELF-HEALING]            │
├──────────────────────────────────────────────────────────┤
│ DEVICE ID:   {device_id:<43} │
│ RULE ID:     {rule_id:<43} │
│ PARAMETER:   {parameter:<43} │
│ SEVERITY:    HIGH                                        │
├──────────────────────────────────────────────────────────┤
│ COMMAND:     {remediation_command[:43]:<43} │
├──────────────────────────────────────────────────────────┤
│ [MDM STDOUT] Initiating execution of self-healing payload│
│ [MDM STDOUT] Execution result: SUCCESS                   │
│ [MDM STDOUT] Verification: compliant state reconciled.  │
│ [STATUS]     AUTOMATED MITIGATION APPLIED SUCCESSFULLY   │
└──────────────────────────────────────────────────────────┘
"""
            print(banner, flush=True)

            remediation_logs = (
                f"[MDM STDOUT] Target: {device_id}\n"
                f"[MDM STDOUT] Executing: {remediation_command}\n"
                "[MDM STDOUT] Verifying setting state...\n"
                f"[MDM STDOUT] Value has been successfully reconciled to match: '{expected_value}'\n"
                "[STATUS] Automated fix executed successfully via mock MDM controller."
            )
            logger.info(f"Tier 2 Remediation applied to {device_id}: Automated self-healing executed.")

        elif severity == SeverityLevel.CRITICAL:
            # ── Tier 3: Stateless Quarantine ──────────────────────────────────
            action_taken = RemediationAction.QUARANTINED
            remediation_timestamp = datetime.now(timezone.utc)
            
            # Trigger quarantine
            remediation_logs = quarantine_device(
                device_id=device_id,
                rule_id=rule_id,
                suggested_id=suggested_id,
                parameter=parameter
            )
            logger.warning(f"Tier 3 Remediation applied to {device_id}: Device Quarantined.")

        # Build and return the fully enriched ComplianceViolation model
        return ComplianceViolation(
            device_id=device_id,
            device_name=device_name,
            os_type=os_type,
            rule_id=rule_id,
            suggested_id=suggested_id,
            technical_parameter=parameter,
            expected_value=expected_value,
            actual_value=actual_value,
            logic_operator=logic,
            severity=raw_severity,
            action_taken=action_taken,
            remediation_command=remediation_command,
            remediation_logs=remediation_logs,
            remediation_timestamp=remediation_timestamp,
            grace_period_expires_at=grace_period_expires_at,
        )
