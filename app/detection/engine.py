"""Central anomaly detection engine orchestrating statistical and graph-based detectors."""
import json
import logging
from typing import Dict, List, Any, Optional
from app.detection.zscore_detector import RollingZScoreDetector
from app.detection.graph_detector import NetworkXGraphDetector

logger = logging.getLogger("sentinel.detection")


class AnomalyEngine:
    """Unified coordinator for real-time anomaly detection across statistical and graph models."""

    def __init__(self):
        self.zscore_detector = RollingZScoreDetector()
        self.graph_detector = NetworkXGraphDetector()

    def process_event(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate an incoming access event across both detection engines.

        Returns list of flagged anomalies (if any).
        """
        username = event.get("username", "anonymous")
        resource_key = event.get("resource_key", "UNKNOWN")
        resource_type = event.get("resource_type", "GENERIC")
        sensitivity_level = event.get("sensitivity_level", "INTERNAL")
        timestamp = event.get("timestamp")

        flagged_anomalies: List[Dict[str, Any]] = []

        # 1. Statistical Rolling Z-Score Evaluation
        try:
            z_anomaly = self.zscore_detector.process_event(
                username=username,
                resource_key=resource_key,
                event_time=timestamp,
            )
            if z_anomaly:
                flagged_anomalies.append(z_anomaly)
        except Exception as e:
            logger.error(f"Error in Z-Score detector: {e}", exc_info=True)

        # 2. NetworkX Structural Graph Evaluation
        try:
            graph_anomalies = self.graph_detector.process_event(
                username=username,
                resource_key=resource_key,
                resource_type=resource_type,
                sensitivity_level=sensitivity_level,
                event_time=timestamp,
            )
            if graph_anomalies:
                flagged_anomalies.extend(graph_anomalies)
        except Exception as e:
            logger.error(f"Error in Graph detector: {e}", exc_info=True)

        return flagged_anomalies

    def get_topology(self) -> Dict[str, Any]:
        """Return the current NetworkX topology for UI rendering."""
        return self.graph_detector.get_topology()

    def reset(self):
        """Reset detectors for testing or clean slate."""
        self.zscore_detector.reset()
        self.graph_detector.reset()


# Singleton instance shared by streaming worker
detection_engine = AnomalyEngine()
