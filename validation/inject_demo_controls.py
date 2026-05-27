"""
Utility script to inject a diverse, balanced set of security controls (rules)
into MongoDB that align perfectly with the telemetry producer's simulation profile.

This ensures your live demo populates:
- Yellow (Grace Period / LOW severity)
- Red (Non-Compliant / MEDIUM severity)
- Purple (Quarantined / CRITICAL severity)
- Green (Compliant / HEALTHY fleet devices)

Run with:
    python -m validation.inject_demo_controls
"""
import sys
import os
import httpx
from datetime import datetime, timezone

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.storage import RuleStore
from db.schema import SecurityRule, LogicOperator, SeverityLevel

def main():
    try:
        store = RuleStore()
    except Exception as e:
        print(f"[-] MongoDB connection failed: {e}. Make sure MongoDB is running.")
        sys.exit(1)

    print("[*] Preparing demo rules to inject...")

    demo_rules = [
        # --- LOW Severity (Yellow / Grace Period) ---
        SecurityRule(
            rule_id="demo-screen-lock-1234",
            suggested_id="AC-1.1-LOCK",
            category="Access Control",
            technical_parameter="screen_lock_timeout",
            expected_value="300",
            logic=LogicOperator.LESS_THAN_OR_EQUAL,
            severity=SeverityLevel.LOW,
            source_document="policy.pdf",
            chunk_reference="Security Policy Section 4 (Page 2)",
            remediation_command_terminal="sudo sysadminctl -screenLock 300",
            remediation="Set screen lock inactivity timeout to 300 seconds."
        ),
        SecurityRule(
            rule_id="demo-os-update-1234",
            suggested_id="OS-1.2-UPDATE",
            category="Patch Management",
            technical_parameter="os_auto_update",
            expected_value="true",
            logic=LogicOperator.EQUALS,
            severity=SeverityLevel.LOW,
            source_document="policy.pdf",
            chunk_reference="Security Policy Section 8 (Page 4)",
            remediation_command_terminal="softwareupdate --schedule on",
            remediation="Enable automatic operating system updates."
        ),
        SecurityRule(
            rule_id="demo-min-password-1234",
            suggested_id="AC-1.3-PASS",
            category="Access Control",
            technical_parameter="min_password_length",
            expected_value="12",
            logic=LogicOperator.GREATER_THAN_OR_EQUAL,
            severity=SeverityLevel.LOW,
            source_document="policy.pdf",
            chunk_reference="Security Policy Section 3 (Page 1)",
            remediation_command_terminal="pwpolicy -setpolicy 'minLen=12'",
            remediation="Set minimum system password length to 12 characters."
        ),

        # --- MEDIUM/HIGH Severity (Red / Non-Compliant / Reviewable) ---
        SecurityRule(
            rule_id="demo-firewall-1234",
            suggested_id="NW-2.1-FIREWALL",
            category="Network Security",
            technical_parameter="firewall_enabled",
            expected_value="true",
            logic=LogicOperator.EQUALS,
            severity=SeverityLevel.MEDIUM,
            source_document="policy.pdf",
            chunk_reference="Security Policy Section 5 (Page 3)",
            remediation_command_terminal="sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on",
            remediation="Turn on system Application Firewall."
        ),
        SecurityRule(
            rule_id="demo-password-age-1234",
            suggested_id="AC-2.2-PASS-AGE",
            category="Access Control",
            technical_parameter="max_password_age",
            expected_value="90",
            logic=LogicOperator.LESS_THAN_OR_EQUAL,
            severity=SeverityLevel.MEDIUM,
            source_document="policy.pdf",
            chunk_reference="Security Policy Section 3 (Page 1)",
            remediation_command_terminal="pwpolicy -setpolicy 'maxAge=90'",
            remediation="Set maximum password age to 90 days."
        ),

        # --- CRITICAL Severity (Purple / Automatic Quarantine) ---
        SecurityRule(
            rule_id="demo-disk-encryption-1234",
            suggested_id="DP-3.1-ENCRYPT",
            category="Data Protection",
            technical_parameter="disk_encryption",
            expected_value="true",
            logic=LogicOperator.EQUALS,
            severity=SeverityLevel.CRITICAL,
            source_document="policy.pdf",
            chunk_reference="Security Policy Section 2 (Page 1)",
            remediation_command_terminal="sudo fdesetup enable",
            remediation="Turn on FileVault disk encryption."
        ),
        SecurityRule(
            rule_id="demo-ssh-root-1234",
            suggested_id="NW-3.2-SSH",
            category="Network Security",
            technical_parameter="ssh_root_login",
            expected_value="false",
            logic=LogicOperator.EQUALS,
            severity=SeverityLevel.CRITICAL,
            source_document="policy.pdf",
            chunk_reference="Security Policy Section 9 (Page 5)",
            remediation_command_terminal="sudo sed -i '' 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config",
            remediation="Disable root login access over SSH."
        )
    ]

    print("[*] Injecting demo controls into MongoDB...")
    stats = store.upsert_rules_batch(demo_rules)
    print(f"[+] Injection complete: {stats}")

    # Reload rules cache in the backend
    try:
        resp = httpx.post("http://127.0.0.1:8000/rules/reload", timeout=5.0)
        if resp.status_code == 200:
            print("[+] Successfully reloaded backend rules cache!")
        else:
            print(f"[-] Backend reload returned status: {resp.status_code}")
    except Exception as e:
        print(f"[!] Could not notify backend to reload (is uvicorn running?): {e}")

if __name__ == "__main__":
    main()
