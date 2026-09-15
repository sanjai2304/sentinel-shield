"""Background realistic traffic simulator generating continuous access events."""
import asyncio
import random
import time
import logging
from typing import Dict, Any, Optional
from app.config import settings
from app.streaming.event_bus import publish_event

logger = logging.getLogger("sentinel.simulator")

# Realistic enterprise employee roles and their standard, authorized daily resources
ENTERPRISE_USER_PROFILES = [
    {
        "username": "analyst_alice",
        "role": "analyst",
        "department": "Threat Intelligence",
        "resources": [
            ("INTERNAL_STAFF_DIR", "DIRECTORY", "INTERNAL"),
            ("CUSTOMER_CRM_DB", "DATABASE", "CONFIDENTIAL"),
            ("INTERNAL_STAFF_DIR", "DIRECTORY", "INTERNAL"),
        ],
        "ip": "10.0.1.15",
    },
    {
        "username": "analyst_bob",
        "role": "analyst",
        "department": "Data Compliance",
        "resources": [
            ("CUSTOMER_CRM_DB", "DATABASE", "CONFIDENTIAL"),
            ("FINANCIAL_LEDGER_Q3", "LEDGER", "RESTRICTED"),
            ("CUSTOMER_CRM_DB", "DATABASE", "CONFIDENTIAL"),
        ],
        "ip": "10.0.2.42",
    },
    {
        "username": "analyst_carol",
        "role": "analyst",
        "department": "Incident Response",
        "resources": [
            ("INTERNAL_STAFF_DIR", "DIRECTORY", "INTERNAL"),
            ("EXECUTIVE_BOARD_MINUTES", "DOCUMENT_STORE", "RESTRICTED"),
            ("INTERNAL_STAFF_DIR", "DIRECTORY", "INTERNAL"),
        ],
        "ip": "10.0.3.88",
    },
]

ACTIONS = ["READ", "READ", "READ", "SEARCH", "READ", "EXPORT"]


class TrafficSimulator:
    """Simulates realistic enterprise background traffic to continuous ingestion pipeline.

    Generates varied, legitimate, normal-hours employee access events matching authorized
    department profiles so that normal traffic generates 0% false positive anomalies.
    """

    def __init__(self):
        self.is_running: bool = False
        self.delay_seconds: float = settings.SIMULATOR_DEFAULT_DELAY_SECONDS
        self._task: Optional[asyncio.Task] = None
        self.events_generated: int = 0

    def start(self, delay_seconds: Optional[float] = None):
        """Start the background traffic loop."""
        if delay_seconds is not None:
            self.delay_seconds = delay_seconds
        
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info(f"Traffic simulator started with {self.delay_seconds}s interval.")

    def stop(self):
        """Pause or stop the background traffic loop."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Traffic simulator paused.")

    def set_speed(self, multiplier: float):
        """Adjust delay according to multiplier (e.g. 1x, 3x, 8x)."""
        base_delay = 2.5
        self.delay_seconds = max(0.3, base_delay / max(0.1, multiplier))
        logger.info(f"Simulator speed adjusted: delay={self.delay_seconds:.2f}s")

    async def _run_loop(self):
        while self.is_running:
            try:
                # Select an employee and an authorized resource from their job profile
                profile = random.choice(ENTERPRISE_USER_PROFILES)
                user = profile["username"]
                user_role = profile["role"]
                client_ip = profile["ip"]

                res_key, res_type, sensitivity = random.choice(profile["resources"])
                action = random.choice(ACTIONS)

                event = {
                    "username": user,
                    "user_role": user_role,
                    "resource_key": res_key,
                    "resource_type": res_type,
                    "sensitivity_level": sensitivity,
                    "action": action,
                    "client_ip": client_ip,
                    "status_code": 200,
                    "latency_ms": round(random.uniform(6.0, 24.0), 1),
                    "is_synthetic": True,
                    "timestamp": time.time(),
                }

                await publish_event(event)
                self.events_generated += 1

                # Jitter delay slightly (normal human work pattern)
                jitter = random.uniform(0.8, 1.4)
                await asyncio.sleep(self.delay_seconds * jitter)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in simulator loop: {e}", exc_info=True)
                await asyncio.sleep(1.0)

    def get_status(self) -> Dict[str, Any]:
        """Return current status of simulator."""
        return {
            "is_running": self.is_running,
            "delay_seconds": round(self.delay_seconds, 2),
            "events_generated": self.events_generated,
        }


simulator = TrafficSimulator()
