"""
FastAPI telemetry ingestor service.

Receives device telemetry via POST /telemetry, feeds it into an
asyncio.Queue, and manages the StreamProcessor worker lifecycle
via FastAPI's lifespan context manager.

Run with:
    python -m uvicorn validation.ingestor:app --host 127.0.0.1 --port 8000 --workers 1
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from pipeline.logger import get_logger
from db.storage import RuleStore
from validation.models import TelemetryPayload, RemediationAction
from validation.processor import StreamProcessor
from validation.queue_interface import BaseTelemetryQueue, InMemoryTelemetryQueue, RedisTelemetryQueue
import redis.asyncio as redis
import time
import random
from datetime import datetime, timezone

logger = get_logger(__name__)

# ── Observability State ──────────────────────────────────────────────────────
class MonitoringState:
    def __init__(self):
        self.total_telemetry_events_received = 0
        self.total_telemetry_events_processed = 0
        self.total_violations_detected = 0
        self.total_processing_latency_ms = 0.0

_monitoring = MonitoringState()

# ── Shared state (module-level) ──────────────────────────────────────────────
_queue: BaseTelemetryQueue | None = None
_redis_client: redis.Redis | None = None
_rules_cache: dict = {}
_store: RuleStore | None = None
_processor_task: asyncio.Task | None = None


async def _load_rules_cache() -> int:
    """Fetch all rules from MongoDB into the in-memory cache. Returns count."""
    global _rules_cache
    rules_dict = await asyncio.to_thread(_store.get_all_rules_as_dict)
    _rules_cache.clear()
    _rules_cache.update(rules_dict)
    return len(_rules_cache)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: connect to MongoDB, load rules cache, start the processor.
    Shutdown: send sentinel, drain queue, wait for processor to finish.
    """
    global _queue, _store, _processor_task, _redis_client

    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Ingestor starting up...")

    # 1. Connect to MongoDB (synchronous — offload to thread)
    _store = await asyncio.to_thread(RuleStore)

    # 2. Load rules cache
    count = await _load_rules_cache()
    logger.info(f"Loaded {count} rules into cache.")

    # 3. Create bounded queue (backpressure)
    if config.QUEUE_TYPE.lower() == "redis":
        _redis_client = redis.from_url(config.REDIS_URI)
        _queue = RedisTelemetryQueue(redis_client=_redis_client, queue_key=config.REDIS_QUEUE_KEY)
        logger.info(f"Using RedisTelemetryQueue connected to {config.REDIS_URI}")
    else:
        _queue = InMemoryTelemetryQueue(maxsize=config.TELEMETRY_QUEUE_MAX_SIZE)
        logger.info("Using InMemoryTelemetryQueue")

    # 4. Start the stream processor as a background task
    processor = StreamProcessor(
        queue=_queue,
        rules_cache=_rules_cache,
        store=_store,
        monitoring_state=_monitoring,
    )
    _processor_task = asyncio.create_task(processor.run())

    logger.info("Ingestor ready — accepting telemetry.")

    yield  # ← app is running

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Ingestor shutting down — draining queue...")

    # Send sentinel to stop the processor
    await _queue.put(None)

    # Wait for the processor to finish draining
    if _processor_task is not None:
        await _processor_task

    if _redis_client is not None:
        await _redis_client.aclose()

    logger.info("Ingestor shutdown complete.")


# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Compliance Telemetry Ingestor",
    description="Receives device telemetry and validates against the rules registry.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/telemetry", status_code=202)
async def ingest_telemetry(payload: TelemetryPayload):
    """
    Accept a telemetry payload and enqueue it for async processing.
    Returns 202 Accepted immediately — validation happens in the background.
    """
    if _queue is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    await _queue.put(payload)
    _monitoring.total_telemetry_events_received += 1

    return {
        "status": "accepted",
        "device_id": payload.device_id,
        "parameter": payload.technical_parameter,
        "queue_size": await _queue.qsize(),
    }


@app.post("/rules/reload")
async def reload_rules():
    """
    Re-fetch all rules from MongoDB into the in-memory cache.
    Call this after ingesting a new PDF into the rules registry.
    """
    count = await _load_rules_cache()
    return {"status": "reloaded", "rules_count": count}


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "rules_cached": len(_rules_cache),
        "queue_size": await _queue.qsize() if _queue else 0,
    }

@app.get("/metrics")
async def get_metrics():
    """Prometheus-compatible metrics endpoint."""
    metrics = [
        "# HELP swif_telemetry_received_total Total telemetry events received",
        "# TYPE swif_telemetry_received_total counter",
        f"swif_telemetry_received_total {_monitoring.total_telemetry_events_received}",
        "",
        "# HELP swif_telemetry_processed_total Total telemetry events processed",
        "# TYPE swif_telemetry_processed_total counter",
        f"swif_telemetry_processed_total {_monitoring.total_telemetry_events_processed}",
        "",
        "# HELP swif_violations_detected_total Total violations detected",
        "# TYPE swif_violations_detected_total counter",
        f"swif_violations_detected_total {_monitoring.total_violations_detected}",
        "",
        "# HELP swif_processing_latency_ms_total Cumulative processing latency in ms",
        "# TYPE swif_processing_latency_ms_total counter",
        f"swif_processing_latency_ms_total {_monitoring.total_processing_latency_ms}",
    ]
    
    if _queue:
        metrics.extend([
            "",
            "# HELP swif_queue_size Current size of the telemetry queue",
            "# TYPE swif_queue_size gauge",
            f"swif_queue_size {await _queue.qsize()}",
        ])
        
    return "\n".join(metrics)

# ── Dashboard API Endpoints ──────────────────────────────────────

@app.get("/api/score")
async def get_compliance_score():
    """Returns an overall compliance score."""
    total_rules = len(_rules_cache)
    if total_rules == 0:
        return {"score": 100.0, "total_rules": 0, "active_violations": 0}
        
    # Get active violations count from DB
    active_violations = await asyncio.to_thread(
        _store.count_violations, 
        status_filter="all" # could optionally filter to non-remediated
    )
    
    # We define score based on active violations over total rules
    score = max(0.0, (1.0 - (active_violations / total_rules))) * 100
    
    return {
        "score": round(score, 1),
        "total_rules": total_rules,
        "active_violations": active_violations
    }

@app.get("/api/rules")
async def get_rules(limit: int = 200, skip: int = 0):
    """Returns unique rules from the database."""
    # Note: get_all_rules currently doesn't support pagination, but we can return all and paginate or just return all unique
    rules = await asyncio.to_thread(_store.get_all_rules, unique=True)
    return rules[skip:skip+limit]

@app.get("/api/devices/count")
async def get_device_count():
    """Returns the number of unique devices reporting violations."""
    count = await asyncio.to_thread(_store.get_unique_device_count)
    return {"count": count}

@app.get("/api/violations")
async def get_violations(limit: int = 100, skip: int = 0, status: str = "all"):
    """Returns paginated violations."""
    violations = await asyncio.to_thread(
        _store.get_all_violations,
        limit=limit,
        skip=skip,
        status_filter=status
    )
    return violations

@app.post("/api/remediate/{violation_id}")
async def remediate_violation(violation_id: str):
    """Executes a fix for a specific LOGGED_FOR_REVIEW violation."""
    violation = await asyncio.to_thread(_store.get_violation_by_id, violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
        
    if violation.get("action_taken") != RemediationAction.LOGGED_FOR_REVIEW.value:
        raise HTTPException(status_code=400, detail="Violation is not in a reviewable state")
        
    # Simulate remediation execution
    command = violation.get("remediation_command", "sudo fix-compliance")
    logs = (
        f"[MDM STDOUT] Target: {violation.get('device_id')}\n"
        f"[MDM STDOUT] Executing manual fix requested via dashboard: {command}\n"
        "[MDM STDOUT] Verifying setting state...\n"
        f"[MDM STDOUT] Value has been successfully reconciled to match: '{violation.get('expected_value')}'\n"
        "[STATUS] Fix executed successfully."
    )
    
    update_data = {
        "action_taken": RemediationAction.AUTOMATED_FIX.value,
        "remediation_logs": logs,
        "remediation_timestamp": datetime.now(timezone.utc)
    }
    
    success = await asyncio.to_thread(
        _store.update_violation,
        violation_id,
        update_data
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update violation in DB")
        
    return {"status": "success", "logs": logs}

@app.post("/api/simulate-drift")
async def simulate_drift():
    """Generates a dummy violation by submitting a bad telemetry payload."""
    if not _rules_cache:
        raise HTTPException(status_code=400, detail="No rules loaded to simulate drift against.")
        
    # Pick a random rule
    rule_key = random.choice(list(_rules_cache.keys()))
    rule = _rules_cache[rule_key]
    
    os_types = ["android", "ios", "chrome"]
    os_type = random.choice(os_types)
    device_id = f"simulated-{os_type.lower()}-{random.randint(100, 999)}"
    
    if os_type == "android":
        device_name = f"Android-Tablet-{random.randint(10, 99)}"
    elif os_type == "ios":
        device_name = f"iPad-Air-{random.randint(10, 99)}"
    else:
        device_name = f"Chromebook-{random.randint(10, 99)}"
    
    # Craft a non-compliant value
    # If expected is 'yes', we send 'no', etc.
    expected = rule.get("expected_value", "")
    if expected.lower() == "yes":
        bad_value = "no"
    elif expected.lower() == "true":
        bad_value = "false"
    elif expected.isdigit():
        bad_value = str(int(expected) + 100) # Assuming less than is required
    else:
        bad_value = "non_compliant_value"
        
    payload = TelemetryPayload(
        device_id=device_id,
        device_name=device_name,
        os_type=os_type,
        technical_parameter=rule.get("technical_parameter"),
        value=bad_value
    )
    
    # Inject into the queue
    if _queue is not None:
        await _queue.put(payload)
    
    return {
        "status": "simulated",
        "device_id": device_id,
        "parameter": payload.technical_parameter
    }
