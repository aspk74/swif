"""
Unit tests for the SWIF compliance Remediation Layer.
"""
import pytest
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from validation.remediation import RemediationManager, quarantine_device
from validation.models import RemediationAction
from db.schema import SeverityLevel


class TestRemediationFallbacks:
    def test_remediation_command_terminal_used(self):
        manager = RemediationManager()
        rule = {
            "rule_id": "test-rule-1",
            "suggested_id": "RULE-1",
            "technical_parameter": "test_param",
            "expected_value": "1",
            "logic": "EQUALS",
            "severity": "LOW",
            "remediation_command_terminal": "sudo rm -rf /tmp/dangerous",
            "remediation": "Delete dangerous folder",
        }
        violation = manager.evaluate_violation("device-001", rule, "0")
        assert violation.remediation_command == "sudo rm -rf /tmp/dangerous"

    def test_remediation_textual_used_as_fallback(self):
        manager = RemediationManager()
        rule = {
            "rule_id": "test-rule-2",
            "suggested_id": "RULE-2",
            "technical_parameter": "test_param",
            "expected_value": "1",
            "logic": "EQUALS",
            "severity": "LOW",
            "remediation": "Manually clean cache",
        }
        violation = manager.evaluate_violation("device-001", rule, "0")
        assert violation.remediation_command == "Manually clean cache"

    def test_generic_fallback_when_both_missing(self):
        manager = RemediationManager()
        rule = {
            "rule_id": "test-rule-3",
            "suggested_id": "RULE-3",
            "technical_parameter": "custom_param_name",
            "expected_value": "1",
            "logic": "EQUALS",
            "severity": "LOW",
        }
        violation = manager.evaluate_violation("device-001", rule, "0")
        assert violation.remediation_command == "sudo compliance-fix --parameter custom_param_name"


class TestTier1Remediation:
    @pytest.mark.parametrize("severity", ["LOW", "MEDIUM"])
    def test_tier1_review_only(self, severity):
        manager = RemediationManager()
        rule = {
            "rule_id": f"test-rule-{severity}",
            "suggested_id": "RULE-LOW-MED",
            "technical_parameter": "low_med_param",
            "expected_value": "1",
            "logic": "EQUALS",
            "severity": severity,
            "remediation": "Do manual check",
        }
        violation = manager.evaluate_violation("device-001", rule, "0")
        assert violation.action_taken == RemediationAction.LOGGED_FOR_REVIEW
        assert violation.remediation_timestamp is None
        assert "Manual operator review recommended" in violation.remediation_logs
        assert "Do manual check" in violation.remediation_logs


class TestTier2Remediation:
    def test_tier2_automated_fix(self, capsys):
        manager = RemediationManager()
        rule = {
            "rule_id": "test-rule-high",
            "suggested_id": "RULE-HIGH",
            "technical_parameter": "high_severity_param",
            "expected_value": "enabled",
            "logic": "EQUALS",
            "severity": "HIGH",
            "remediation_command_terminal": "defaults write com.security auto_update 1",
        }
        
        violation = manager.evaluate_violation("device-win-002", rule, "disabled")
        
        # Verify console output
        captured = capsys.readouterr()
        assert "[MDM AUTOMATED SELF-HEALING]" in captured.out
        assert "device-win-002" in captured.out
        
        # Verify violation data
        assert violation.action_taken == RemediationAction.AUTOMATED_FIX
        assert violation.remediation_command == "defaults write com.security auto_update 1"
        assert isinstance(violation.remediation_timestamp, datetime)
        assert "[MDM STDOUT] Executing: defaults write com.security auto_update 1" in violation.remediation_logs
        assert "successfully reconciled to match: 'enabled'" in violation.remediation_logs


class TestTier3Remediation:
    def test_tier3_quarantine(self, capsys):
        manager = RemediationManager()
        rule = {
            "rule_id": "test-rule-critical",
            "suggested_id": "RULE-CRITICAL",
            "technical_parameter": "critical_param",
            "expected_value": "1",
            "logic": "EQUALS",
            "severity": "CRITICAL",
            "remediation": "Isolate from internet immediately",
        }
        
        violation = manager.evaluate_violation("device-linux-003", rule, "0")
        
        # Verify console output
        captured = capsys.readouterr()
        assert "[CRITICAL VIOLATION - DEVICE ISOLATED]" in captured.out
        assert "device-linux-003" in captured.out
        
        # Verify violation data
        assert violation.action_taken == RemediationAction.QUARANTINED
        assert isinstance(violation.remediation_timestamp, datetime)
        assert "Initiating quarantine sequence for device-linux-003" in violation.remediation_logs
        assert "DEVICE SUCCESSFULLY QUARANTINED & SILENCED" in captured.out
