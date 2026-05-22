"""
Asynchronous stream processor for telemetry validation.

Pulls TelemetryPayload items from an asyncio.Queue, validates them
against the in-memory rules cache, and persists violations to MongoDB
via asyncio.to_thread() to avoid blocking the event loop.
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.logger import get_logger
from validation.models import TelemetryPayload, ComplianceViolation, RemediationAction
from validation.comparator import check_compliance
from validation.remediation import RemediationManager
from validation.remediation import RemediationManager
from validation.queue_interface import BaseTelemetryQueue
from db.schema import LogicOperator
from db.storage import RuleStore
import time

logger = get_logger(__name__)


class StreamProcessor:
    """
    Async worker that consumes telemetry from a queue, validates
    against cached rules, and writes violations to MongoDB.
    """

    def __init__(
        self,
        queue: BaseTelemetryQueue,
        rules_cache: dict,
        store: RuleStore,
        monitoring_state=None,
    ):
        self.queue = queue
        self.rules_cache = rules_cache
        self.store = store
        self.remediation_manager = RemediationManager()
        self._monitoring_state = monitoring_state
        self._processed = 0
        self._violations = 0

    async def run(self):
        """
        Main worker loop. Exits cleanly when it receives a None sentinel.
        """
        logger.info("StreamProcessor started — waiting for telemetry events...")

        while True:
            item = await self.queue.get()

            # Sentinel check — graceful shutdown
            if item is None:
                logger.info(
                    f"StreamProcessor shutting down. "
                    f"Processed={self._processed}, Violations={self._violations}"
                )
                self.queue.task_done()
                break

            try:
                start_time = time.time()
                await self._process_event(item)
                latency_ms = (time.time() - start_time) * 1000
                if self._monitoring_state:
                    self._monitoring_state.total_processing_latency_ms += latency_ms
                    self._monitoring_state.total_telemetry_events_processed += 1
            except Exception as e:
                logger.error(f"Error processing telemetry event: {e}")
            finally:
                self.queue.task_done()
                self._processed += 1

    async def _process_event(self, payload: TelemetryPayload):
        """Validate a single telemetry event against the rules cache."""
        rule = self.rules_cache.get(payload.technical_parameter)

        if rule is None:
            # No rule covers this parameter — nothing to validate
            logger.info(
                f"No rule for parameter '{payload.technical_parameter}' "
                f"from device '{payload.device_id}'. Skipping."
            )
            return

        # Evaluate compliance
        logic = LogicOperator(rule["logic"])
        is_compliant = check_compliance(
            actual_value=payload.value,
            expected_value=rule["expected_value"],
            logic=logic,
        )

        if is_compliant:
            logger.info(
                f"COMPLIANT: device={payload.device_id}, "
                f"param={payload.technical_parameter}, value={payload.value}"
            )
            return

        # --- Violation detected ---
        self._violations += 1
        if self._monitoring_state:
            self._monitoring_state.total_violations_detected += 1

        # Evaluate tiered remediation via the RemediationManager
        violation = self.remediation_manager.evaluate_violation(
            device_id=payload.device_id,
            rule=rule,
            actual_value=payload.value,
            device_name=payload.device_name,
            os_type=payload.os_type
        )

        logger.warning(
            f"VIOLATION: device={payload.device_id}, "
            f"param={payload.technical_parameter}, "
            f"expected={rule['expected_value']} ({logic.value}), "
            f"actual={payload.value}, "
            f"severity={rule.get('severity')}, "
            f"remediation_action={violation.action_taken.value}"
        )

        # Persist to MongoDB — offloaded to thread to avoid blocking the event loop
        await asyncio.to_thread(
            self.store.insert_violation,
            violation.model_dump(mode="json"),
        )
