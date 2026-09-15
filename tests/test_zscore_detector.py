"""Unit tests for the Rolling Z-Score Anomaly Detector."""
import time
import pytest
from app.detection.zscore_detector import RollingZScoreDetector


def test_zscore_normal_traffic_no_anomaly():
    detector = RollingZScoreDetector(window_seconds=60, threshold=3.0, min_events=3)
    detector.reset()

    base_time = 100000.0
    # Simulate steady normal rate: 1 request every 12 seconds
    anomalies = []
    for i in range(10):
        t = base_time + i * 12.0
        anom = detector.process_event("analyst_bob", "CUSTOMER_CRM_DB", event_time=t)
        if anom:
            anomalies.append(anom)

    assert len(anomalies) == 0, "Normal steady traffic should not trigger Z-Score anomalies"


def test_zscore_burst_triggers_anomaly():
    detector = RollingZScoreDetector(window_seconds=60, threshold=3.0, min_events=3)
    detector.reset()

    base_time = 200000.0
    # 1. Establish low baseline: 5 spaced events
    for i in range(5):
        detector.process_event("analyst_bob", "PII_CUSTOMER_VAULT", event_time=base_time + i * 15.0)

    # 2. Inject rapid burst of 25 requests in 10 seconds
    burst_start = base_time + 100.0
    triggered = None
    for j in range(25):
        t = burst_start + (j * 0.4)
        anom = detector.process_event("analyst_bob", "PII_CUSTOMER_VAULT", event_time=t)
        if anom:
            triggered = anom
            break

    assert triggered is not None, "Rapid burst should cleanly trigger Z-Score frequency anomaly"
    assert triggered["anomaly_type"] == "FREQUENCY_ZSCORE"
    assert triggered["score"] >= 3.0
    assert "Z-Score" in triggered["explanation"]
    assert "analyst_bob" in triggered["explanation"]
    assert "PII_CUSTOMER_VAULT" in triggered["explanation"]
    assert triggered["details"]["current_rate_in_window"] > 5
