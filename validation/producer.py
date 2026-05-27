"""
Mock telemetry producer.

Simulates a device fleet sending security state updates to the ingestor.
Generates a mix of compliant and non-compliant values based on the rules 
currently in the MongoDB registry.

Run with:
    python -m validation.producer

Requires the ingestor to be running on INGESTOR_HOST:INGESTOR_PORT.
"""
import random
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from pipeline.logger import get_logger

logger = get_logger(__name__)

# ── Mock device fleet ────────────────────────────────────────────────────────
DEVICE_IDS = [f"LAPTOP-CORP-{i:03d}" for i in range(1, 26)]

# Specific Target Devices for exact visualization
QUARANTINE_DEVICES = {"LAPTOP-CORP-001", "LAPTOP-CORP-002", "LAPTOP-CORP-003"}    # CRITICAL -> Purple
GRACE_PERIOD_DEVICES = {"LAPTOP-CORP-004", "LAPTOP-CORP-005", "LAPTOP-CORP-006", "LAPTOP-CORP-007"} # LOW -> Yellow
EXECUTE_FIX_DEVICES = {"LAPTOP-CORP-008", "LAPTOP-CORP-009"}   # MEDIUM -> Red
BREACH_DEVICE_IDS = QUARANTINE_DEVICES | GRACE_PERIOD_DEVICES | EXECUTE_FIX_DEVICES

REALISTIC_NAMES = [
    "Anushka's MacBook Pro",
    "Rishi's Google Pad",
    "John's ThinkPad",
    "Sarah's iPhone 14",
    "Mike's Dell XPS",
    "Emily's iPad Air",
    "David's Galaxy S23",
    "Chloe's MacBook Air",
    "James's Surface Pro",
    "Lisa's Pixel 8",
    "Tom's Chromebook",
    "Anna's Galaxy Tab",
    "Robert's Mac Studio",
    "Maria's iPhone 15 Pro",
    "William's XPS 15",
    "Sophie's iPad Pro",
    "Richard's ThinkPad T14",
    "Emma's Pixel 7a",
    "Joseph's ROG Zephyrus",
    "Olivia's MacBook Pro 16",
    "Charles's Surface Laptop",
    "Grace's Galaxy Z Fold",
    "Daniel's Alienware m16",
    "Lily's iPhone 13",
    "Matthew's ThinkPad X1"
]

DEVICE_METADATA = {}
for i, dev_id in enumerate(DEVICE_IDS):
    os_type = "chrome" if i % 3 == 0 else ("ios" if i % 3 == 1 else "android")
    DEVICE_METADATA[dev_id] = {
        "device_name": REALISTIC_NAMES[i],
        "os_type": os_type
    }

# ── Sticky Breach State ──────────────────────────────────────────────────────
# Tracks the specific bad values generated for breached devices.
# Format: { device_id: { technical_parameter: bad_value } }
breach_state = {dev_id: {} for dev_id in BREACH_DEVICE_IDS}

# ── Fallback test rules (used when MongoDB is empty or unreachable) ──────────
# Each entry: (technical_parameter, expected_value, logic, bad_values, severity)
FALLBACK_RULES = [
    ("max_password_age", "90", "LESS_THAN_OR_EQUAL", ["120", "180", "365"], "MEDIUM"),
    ("firewall_enabled", "true", "EQUALS", ["false"], "MEDIUM"),
    ("disk_encryption", "true", "EQUALS", ["false"], "CRITICAL"),
    ("screen_lock_timeout", "300", "LESS_THAN_OR_EQUAL", ["600", "900", "0"], "LOW"),
    ("os_auto_update", "true", "EQUALS", ["false"], "LOW"),
    ("antivirus_running", "true", "EQUALS", ["false"], "HIGH"),
    ("ssh_root_login", "false", "EQUALS", ["true"], "CRITICAL"),
    ("min_password_length", "12", "GREATER_THAN_OR_EQUAL", ["4", "6", "8"], "LOW"),
]


def _build_rules_from_db() -> list[dict]:
    """
    Try to load real rules from MongoDB. Falls back to FALLBACK_RULES
    if the DB is empty or unreachable.
    """
    try:
        from db.storage import RuleStore
        store = RuleStore()
        rules = store.get_all_rules(unique=False)
        if rules:
            logger.info(f"Loaded {len(rules)} rules from MongoDB for telemetry generation.")
            return rules
    except Exception as e:
        logger.warning(f"Could not load rules from MongoDB: {e}. Using fallback rules.")

    return []

def _get_target_severity(device_id: str) -> str:
    if device_id in QUARANTINE_DEVICES:
        return "CRITICAL"
    if device_id in GRACE_PERIOD_DEVICES:
        return "LOW"
    if device_id in EXECUTE_FIX_DEVICES:
        return "MEDIUM"
    return "UNKNOWN"

def _compliant_value(expected: str, logic: str) -> str:
    """Create a compliant value based on the logic type."""
    if logic == "NOT_EQUALS":
        return expected + "_compliant"
    if logic == "NOT_CONTAINS":
        return "completely_unrelated_safe_string"
    if logic == "GREATER_THAN":
        try:
            return str(float(expected) + 1)
        except ValueError:
            return expected + "_greater"
    if logic == "LESS_THAN":
        try:
            return str(float(expected) - 1)
        except ValueError:
            return ""  # Empty string is lexicographically smaller than most things
    if logic == "EXISTS":
        return expected if expected else "active"
    if logic == "NOT_EXISTS":
        return ""
    if logic == "REGEX_MATCH":
        # Hacky fallback: just returning expected might not match complex regex,
        # but usually expected in our fallback rules is literal
        return expected
    # EQUALS, CONTAINS, GREATER_THAN_OR_EQUAL, LESS_THAN_OR_EQUAL
    return expected

def _generate_event(device_id: str, rules_from_db: list[dict]) -> dict:
    """
    Generate a single telemetry event.
    """
    is_breach_target = device_id in BREACH_DEVICE_IDS
    target_severity = _get_target_severity(device_id)

    if is_breach_target and breach_state[device_id]:
        # If this device already has a sticky breach, JUST keep emitting that single broken parameter!
        # Do not pick a new random rule to break. This prevents massive accumulation of errors on one device.
        param = list(breach_state[device_id].keys())[0]
        value = breach_state[device_id][param]
    else:
        # Filter rules matching the specific severity we need to break
        valid_rules = []
        if rules_from_db:
            valid_rules = [r for r in rules_from_db if r.get("severity") == target_severity]
        
        if not valid_rules and rules_from_db:
            valid_rules = rules_from_db # fallback if severity missing
            
        if valid_rules and (is_breach_target or random.random() < 0.7):
            rule = random.choice(valid_rules)
            param = rule["technical_parameter"]
            expected = rule["expected_value"]
            logic = rule.get("logic", "EQUALS")
            
            if is_breach_target:
                value = _perturb_value(expected, logic)
                breach_state[device_id][param] = value
            else:
                value = _compliant_value(expected, logic)
        else:
            # Use fallback rules
            fallback_matches = [r for r in FALLBACK_RULES if r[4] == target_severity]
            if not fallback_matches:
                fallback_matches = FALLBACK_RULES
                
            param, expected, logic, bad_values, severity = random.choice(fallback_matches)
            
            if is_breach_target:
                value = random.choice(bad_values)
                breach_state[device_id][param] = value
            else:
                value = _compliant_value(expected, logic)

    meta = DEVICE_METADATA[device_id]
    
    return {
        "device_id": device_id,
        "device_name": meta["device_name"],
        "os_type": meta["os_type"],
        "technical_parameter": param,
        "value": value,
    }


def _perturb_value(expected: str, logic: str) -> str:
    """Create a non-compliant value based on the expected value type."""
    if logic == "EXISTS":
        return ""
    if logic == "NOT_EXISTS":
        return "active"

    # Try numeric perturbation
    try:
        num = float(expected)
        if logic in ("LESS_THAN", "LESS_THAN_OR_EQUAL"):
            return str(int(num * random.uniform(1.5, 3.0)))  # overshoot
        elif logic in ("GREATER_THAN", "GREATER_THAN_OR_EQUAL"):
            return str(max(1, int(num * random.uniform(0.1, 0.5))))  # undershoot
        else:
            return str(int(num + random.choice([-50, -20, 20, 50])))
    except ValueError:
        pass

    # Boolean flip
    if expected.lower() in ("true", "false"):
        return "false" if expected.lower() == "true" else "true"

    # String: append junk
    return expected + "_invalid"


def main():
    """Main producer loop."""
    import httpx

    base_url = f"http://{config.INGESTOR_HOST}:{config.INGESTOR_PORT}"
    logger.info(f"Producer starting — targeting {base_url}/telemetry")

    # Load rules once at startup
    rules_from_db = _build_rules_from_db()

    sent = 0
    errors = 0

    with httpx.Client(timeout=10.0) as client:
        # Quick health check
        try:
            resp = client.get(f"{base_url}/health")
            logger.info(f"Ingestor health: {resp.json()}")
        except httpx.ConnectError:
            logger.error(f"Cannot reach ingestor at {base_url}. Is it running?")
            sys.exit(1)

        while True:
            cycle_start = time.time()
            
            # --- Check for remediated devices ---
            try:
                rem_resp = client.get(f"{base_url}/api/remediated-devices")
                if rem_resp.status_code == 200:
                    healed_items = rem_resp.json()
                    for item in healed_items:
                        h_dev = item.get("device_id")
                        h_param = item.get("technical_parameter")
                        if h_dev in breach_state and h_param in breach_state[h_dev]:
                            del breach_state[h_dev][h_param]
                            logger.info(f"Producer cleared sticky breach for {h_dev} parameter '{h_param}' due to automated fix.")
            except Exception as e:
                logger.error(f"Failed to fetch remediated devices: {e}")
            # -------------------------------------

            # We iterate through all 25 devices in each cycle
            for device_id in DEVICE_IDS:
                event = _generate_event(device_id, rules_from_db)

                try:
                    resp = client.post(f"{base_url}/telemetry", json=event)
                    if resp.status_code == 202:
                        sent += 1
                        logger.info(
                            f"[#{sent}] Sent: device={event['device_id']}, "
                            f"param={event['technical_parameter']}, "
                            f"value={event['value']}"
                        )
                    else:
                        errors += 1
                        logger.warning(f"Unexpected response {resp.status_code}: {resp.text}")

                except httpx.RequestError as e:
                    errors += 1
                    logger.error(f"Request failed: {e}")

                # Small stagger to avoid hammering the API simultaneously
                time.sleep(0.05)
            
            # Ensure at least 30 seconds pass between full fleet cycles
            elapsed = time.time() - cycle_start
            if elapsed < 30.0:
                time.sleep(30.0 - elapsed)


if __name__ == "__main__":
    main()
