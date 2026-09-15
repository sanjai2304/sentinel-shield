"""Specific synthetic attack scenario definitions to demonstrate real-time anomaly detection."""
import asyncio
import time
import logging
from typing import Dict, Any
from app.streaming.event_bus import publish_event

logger = logging.getLogger("sentinel.simulator")

SENSITIVE_RESOURCES = [
    ("FINANCIAL_LEDGER_Q3", "LEDGER", "RESTRICTED"),
    ("PII_CUSTOMER_VAULT", "VAULT", "RESTRICTED"),
    ("PAYROLL_SALARY_DATA", "DATABASE", "RESTRICTED"),
    ("EXECUTIVE_BOARD_MINUTES", "DOCUMENT_STORE", "RESTRICTED"),
    ("SYSTEM_ROOT_CREDENTIALS", "KEY_VAULT", "TOP_SECRET"),
    ("PCI_PAYMENT_TOKENS", "PAYMENT_GATEWAY", "TOP_SECRET"),
    ("CUSTOMER_CRM_DB", "DATABASE", "CONFIDENTIAL"),
]


async def run_exfiltration_spike(username: str = "analyst_bob", count: int = 18) -> Dict[str, Any]:
    """Triggers a high-velocity data exfiltration spike against a single sensitive resource.

    Designed to cleanly trigger the Rolling Z-Score statistical anomaly detector.
    """
    logger.info(f"Injecting Exfiltration Spike attack by {username} ({count} requests)...")
    resource_key = "PII_CUSTOMER_VAULT"
    res_type = "VAULT"
    sensitivity = "RESTRICTED"

    for i in range(count):
        event = {
            "username": username,
            "user_role": "analyst",
            "resource_key": resource_key,
            "resource_type": res_type,
            "sensitivity_level": sensitivity,
            "action": "EXPORT" if i % 3 == 0 else "READ",
            "client_ip": "198.51.100.42",
            "status_code": 200,
            "latency_ms": 12.5,
            "is_synthetic": True,
            "timestamp": time.time(),
        }
        await publish_event(event)
        await asyncio.sleep(0.08)  # Rapid 80ms burst

    return {
        "status": "success",
        "scenario": "exfiltration_spike",
        "user": username,
        "target_resource": resource_key,
        "events_generated": count,
        "expected_detection": "Rolling Z-Score Frequency Anomaly",
    }


async def run_novelty_attack(username: str = "analyst_carol") -> Dict[str, Any]:
    """Triggers an unauthorized privilege boundary leap to a TOP_SECRET resource never seen before.

    Designed to cleanly trigger the NetworkX Bipartite Graph novelty detector.
    """
    logger.info(f"Injecting Graph Novelty attack by {username}...")
    
    # 1. Establish baseline normal activity if needed
    for r_key, r_type, r_sens in [
        ("INTERNAL_STAFF_DIR", "DIRECTORY", "INTERNAL"),
        ("CUSTOMER_CRM_DB", "DATABASE", "CONFIDENTIAL"),
        ("INTERNAL_STAFF_DIR", "DIRECTORY", "INTERNAL"),
    ]:
        await publish_event({
            "username": username,
            "user_role": "analyst",
            "resource_key": r_key,
            "resource_type": r_type,
            "sensitivity_level": r_sens,
            "action": "READ",
            "client_ip": "192.168.1.105",
            "status_code": 200,
            "latency_ms": 8.0,
            "is_synthetic": True,
            "timestamp": time.time(),
        })
        await asyncio.sleep(0.05)

    # 2. Sudden breach into TOP_SECRET key vault
    target_key = "SYSTEM_ROOT_CREDENTIALS"
    target_type = "KEY_VAULT"
    target_sens = "TOP_SECRET"

    event = {
        "username": username,
        "user_role": "analyst",
        "resource_key": target_key,
        "resource_type": target_type,
        "sensitivity_level": target_sens,
        "action": "READ",
        "client_ip": "192.168.1.105",
        "status_code": 200,
        "latency_ms": 15.0,
        "is_synthetic": True,
        "timestamp": time.time(),
    }
    await publish_event(event)

    return {
        "status": "success",
        "scenario": "graph_novelty_breach",
        "user": username,
        "target_resource": target_key,
        "expected_detection": "NetworkX Bipartite Graph Novelty Anomaly",
    }


async def run_fanout_sweep(username: str = "analyst_alice") -> Dict[str, Any]:
    """Rapidly enumerates 6+ distinct sensitive databases within seconds.

    Designed to cleanly trigger the NetworkX Graph Horizontal Fan-Out detector.
    """
    logger.info(f"Injecting Horizontal Fan-Out Sweep attack by {username}...")
    targets = SENSITIVE_RESOURCES[:6]

    for r_key, r_type, r_sens in targets:
        event = {
            "username": username,
            "user_role": "analyst",
            "resource_key": r_key,
            "resource_type": r_type,
            "sensitivity_level": r_sens,
            "action": "READ",
            "client_ip": "203.0.113.88",
            "status_code": 200,
            "latency_ms": 11.2,
            "is_synthetic": True,
            "timestamp": time.time(),
        }
        await publish_event(event)
        await asyncio.sleep(0.12)  # Rapid sweep across 6 tables

    return {
        "status": "success",
        "scenario": "horizontal_fanout_sweep",
        "user": username,
        "distinct_resources_touched": len(targets),
        "expected_detection": "NetworkX Graph High Fan-Out Anomaly",
    }
