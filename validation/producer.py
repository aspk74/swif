"""
Mock telemetry producer.

Simulates a device sending security state updates to the ingestor
every 1–2 seconds. Generates a mix of compliant and non-compliant values
based on the rules currently in the MongoDB registry.

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
DEVICE_IDS = [
    "device-mac-001",
    "device-win-002",
    "device-linux-003",
    "device-mac-004",
    "device-win-005",
]

# ── Fallback test rules (used when MongoDB is empty or unreachable) ──────────
# Each entry: (technical_parameter, expected_value, logic, bad_values)
FALLBACK_RULES = [
    ("max_password_age", "90", "LESS_THAN_OR_EQUAL", ["120", "180", "365"]),
    ("firewall_enabled", "true", "EQUALS", ["false"]),
    ("disk_encryption", "true", "EQUALS", ["false"]),
    ("screen_lock_timeout", "300", "LESS_THAN_OR_EQUAL", ["600", "900", "0"]),
    ("os_auto_update", "true", "EQUALS", ["false"]),
    ("antivirus_running", "true", "EQUALS", ["false"]),
    ("ssh_root_login", "false", "EQUALS", ["true"]),
    ("min_password_length", "12", "GREATER_THAN_OR_EQUAL", ["4", "6", "8"]),
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


def _generate_event(rules_from_db: list[dict]) -> dict:
    """
    Generate a single telemetry event. ~50% chance of being non-compliant.
    """
    device_id = random.choice(DEVICE_IDS)

    if rules_from_db and random.random() < 0.7:
        # Pick a real rule from the DB
        rule = random.choice(rules_from_db)
        param = rule["technical_parameter"]
        expected = rule["expected_value"]

        if random.random() < 0.5:
            # Compliant: send the expected value
            value = expected
        else:
            # Non-compliant: perturb the value
            value = _perturb_value(expected, rule.get("logic", "EQUALS"))
    else:
        # Use fallback rules
        param, expected, logic, bad_values = random.choice(FALLBACK_RULES)

        if random.random() < 0.5:
            value = expected  # compliant
        else:
            value = random.choice(bad_values)  # non-compliant

    return {
        "device_id": device_id,
        "technical_parameter": param,
        "value": value,
    }


def _perturb_value(expected: str, logic: str) -> str:
    """Create a non-compliant value based on the expected value type."""
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
            event = _generate_event(rules_from_db)

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

            delay = random.uniform(1.0, 2.0)
            time.sleep(delay)


if __name__ == "__main__":
    main()
