"""Unit tests for the NetworkX Bipartite Graph Anomaly Detector."""
import pytest
from app.detection.graph_detector import NetworkXGraphDetector


def test_graph_novelty_detection():
    detector = NetworkXGraphDetector(fanout_threshold=5, fanout_window_seconds=60)
    detector.reset()

    base_time = 1000.0

    # 1. Establish profile: analyst only touches INTERNAL directory
    for i in range(4):
        detector.process_event(
            username="analyst_carol",
            resource_key="INTERNAL_STAFF_DIR",
            resource_type="DIRECTORY",
            sensitivity_level="INTERNAL",
            event_time=base_time + i * 5.0,
        )

    # 2. Sudden breach into TOP_SECRET key vault
    anomalies = detector.process_event(
        username="analyst_carol",
        resource_key="SYSTEM_ROOT_CREDENTIALS",
        resource_type="KEY_VAULT",
        sensitivity_level="TOP_SECRET",
        event_time=base_time + 30.0,
    )

    assert len(anomalies) > 0, "Novelty check should trigger on first TOP_SECRET access"
    novel_anom = [a for a in anomalies if a["anomaly_type"] == "NOVEL_RESOURCE_ACCESS"][0]
    assert novel_anom["severity"] == "CRITICAL"
    assert "SYSTEM_ROOT_CREDENTIALS" in novel_anom["explanation"]
    assert "TOP_SECRET" in novel_anom["explanation"]


def test_graph_fanout_detection():
    detector = NetworkXGraphDetector(fanout_threshold=5, fanout_window_seconds=60)
    detector.reset()

    base_time = 5000.0
    resources = [
        ("RES_1", "DB", "RESTRICTED"),
        ("RES_2", "VAULT", "RESTRICTED"),
        ("RES_3", "LEDGER", "RESTRICTED"),
        ("RES_4", "GATEWAY", "RESTRICTED"),
        ("RES_5", "STORAGE", "RESTRICTED"),
    ]

    anomalies = []
    for idx, (res_key, res_type, sens) in enumerate(resources):
        t = base_time + (idx * 2.0)  # All within 10 seconds
        flagged = detector.process_event(
            username="analyst_alice",
            resource_key=res_key,
            resource_type=res_type,
            sensitivity_level=sens,
            event_time=t,
        )
        anomalies.extend(flagged)

    fanout_anoms = [a for a in anomalies if a["anomaly_type"] == "HIGH_FANOUT"]
    assert len(fanout_anoms) >= 1, "Fan-out check should trigger when reaching 5 distinct resources"
    assert "Graph Fan-Out Anomaly" in fanout_anoms[0]["explanation"]
    assert fanout_anoms[0]["details"]["distinct_resource_count"] == 5


def test_graph_topology_export():
    detector = NetworkXGraphDetector()
    detector.reset()

    detector.process_event("user1", "RES_A", "DB", "INTERNAL", 100.0)
    detector.process_event("user1", "RES_B", "VAULT", "RESTRICTED", 101.0)
    detector.process_event("user2", "RES_A", "DB", "INTERNAL", 102.0)

    topology = detector.get_topology()
    assert "nodes" in topology
    assert "edges" in topology
    assert len(topology["nodes"]) >= 4  # user1, user2, RES_A, RES_B
    assert len(topology["edges"]) >= 3
