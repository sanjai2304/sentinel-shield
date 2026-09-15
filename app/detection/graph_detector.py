"""NetworkX-based graph anomaly detector for novel access patterns and horizontal fan-out."""
import time
from collections import defaultdict, deque
from typing import Dict, List, Set, Optional, Any
import networkx as nx
from app.config import settings


class NetworkXGraphDetector:
    """Detects structural graph anomalies in access patterns using NetworkX.

    Maintains:
    1. A bipartite graph G=(User, Resource) with edge frequencies and metadata.
    2. Historical category/classification sets per user to detect first-time privilege leaps.
    3. Rolling sliding windows of distinct resources accessed by each user to detect horizontal fan-out sweeps.
    """

    def __init__(
        self,
        fanout_threshold: int = settings.GRAPH_FANOUT_THRESHOLD,
        fanout_window_seconds: int = settings.GRAPH_FANOUT_WINDOW_SECONDS,
    ):
        self.fanout_threshold = fanout_threshold
        self.fanout_window_seconds = fanout_window_seconds

        # NetworkX Graph: User nodes <-> Resource nodes
        self.graph = nx.Graph()

        # Historical sets per user for explainable novelty checks
        self.user_resource_types: Dict[str, Set[str]] = defaultdict(set)
        self.user_sensitivities: Dict[str, Set[str]] = defaultdict(set)
        self.user_total_events: Dict[str, int] = defaultdict(int)

        # Sliding window for fan-out detection:
        # username -> deque of (timestamp, resource_key, sensitivity_level)
        self.user_recent_accesses: Dict[str, deque] = defaultdict(deque)

        # Fan-out alert cooldown: username -> last_fanout_alert_time
        self.last_fanout_alert_time: Dict[str, float] = defaultdict(float)

        self._seed_baseline_privileges()

    def _seed_baseline_privileges(self):
        """Seed normal authorized baseline profiles so routine work is not flagged as novelty."""
        # Alice (Threat Intelligence): regular access to directory and customer CRM
        self.user_sensitivities["analyst_alice"].update({"INTERNAL", "CONFIDENTIAL"})
        self.user_resource_types["analyst_alice"].update({"DIRECTORY", "DATABASE"})
        self.user_total_events["analyst_alice"] = 15

        # Bob (Data Compliance): regular access to CRM and general ledger
        self.user_sensitivities["analyst_bob"].update({"INTERNAL", "CONFIDENTIAL", "RESTRICTED"})
        self.user_resource_types["analyst_bob"].update({"DIRECTORY", "DATABASE", "LEDGER"})
        self.user_total_events["analyst_bob"] = 15

        # Carol (Incident Response): regular access to directory and executive docs
        self.user_sensitivities["analyst_carol"].update({"INTERNAL", "CONFIDENTIAL", "RESTRICTED"})
        self.user_resource_types["analyst_carol"].update({"DIRECTORY", "DOCUMENT_STORE"})
        self.user_total_events["analyst_carol"] = 15

    def process_event(
        self,
        username: str,
        resource_key: str,
        resource_type: str,
        sensitivity_level: str,
        event_time: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Process access event against graph topology.

        Can detect:
        1. Novel resource type or sensitivity level accessed for the first time by an established user.
        2. Rapid horizontal fan-out (touching many distinct sensitive resources within a short window).

        Returns list of flagged anomalies (may be empty).
        """
        now = event_time if event_time is not None else time.time()
        anomalies: List[Dict[str, Any]] = []

        user_node = f"user:{username}"
        res_node = f"res:{resource_key}"

        # Ensure nodes exist with attributes
        if not self.graph.has_node(user_node):
            self.graph.add_node(user_node, node_type="user", label=username)
        if not self.graph.has_node(res_node):
            self.graph.add_node(
                res_node,
                node_type="resource",
                label=resource_key,
                resource_type=resource_type,
                sensitivity=sensitivity_level,
            )

        # --- 1. Novelty Check (Has this user ever accessed this category/level before?) ---
        user_history_count = self.user_total_events[username]
        known_types = self.user_resource_types[username]
        known_sensitivities = self.user_sensitivities[username]

        is_top_secret = sensitivity_level.upper() == "TOP_SECRET"
        is_novel_type = resource_type not in known_types
        is_novel_sensitivity = sensitivity_level not in known_sensitivities

        # Flag novelty if:
        # A) User accesses TOP_SECRET for the first time, OR
        # B) User with established history accesses RESTRICTED/novel high-risk category never seen
        is_novel_breach = (
            user_history_count >= 3
            and (
                (is_top_secret and is_novel_sensitivity)
                or (sensitivity_level.upper() == "RESTRICTED" and is_novel_sensitivity and is_novel_type)
            )
        )

        if is_novel_breach:
            severity = "CRITICAL" if is_top_secret else "HIGH"
            novel_aspect = "sensitivity classification" if is_novel_sensitivity else "resource type"
            novel_value = sensitivity_level if is_novel_sensitivity else resource_type

            explanation = (
                f"Graph Novelty Anomaly: User '{username}' accessed {novel_aspect} '{novel_value}' "
                f"(resource '{resource_key}') for the first time in their recorded activity graph. "
                f"Prior established profile accessed: {sorted(list(known_sensitivities or known_types))}."
            )

            anomalies.append({
                "anomaly_type": "NOVEL_RESOURCE_ACCESS",
                "severity": severity,
                "score": 4.5 if severity == "CRITICAL" else 3.5,
                "explanation": explanation,
                "details": {
                    "detector": "NetworkXGraphDetector",
                    "check": "Novelty",
                    "resource_type": resource_type,
                    "sensitivity_level": sensitivity_level,
                    "prior_types": list(known_types),
                    "prior_sensitivities": list(known_sensitivities),
                    "total_prior_events": user_history_count,
                },
            })

        # Update historical profile and graph edges
        self.user_resource_types[username].add(resource_type)
        self.user_sensitivities[username].add(sensitivity_level)
        self.user_total_events[username] += 1

        if self.graph.has_edge(user_node, res_node):
            self.graph[user_node][res_node]["weight"] += 1
            self.graph[user_node][res_node]["last_seen"] = now
        else:
            self.graph.add_edge(
                user_node,
                res_node,
                weight=1,
                first_seen=now,
                last_seen=now,
                resource_type=resource_type,
                sensitivity=sensitivity_level,
            )

        # --- 2. Horizontal Fan-Out / Traversal Check ---
        recent = self.user_recent_accesses[username]
        cutoff = now - self.fanout_window_seconds
        while recent and recent[0][0] < cutoff:
            recent.popleft()

        recent.append((now, resource_key, sensitivity_level))

        # Count distinct resources touched in recent window
        distinct_resources = {item[1] for item in recent}
        distinct_count = len(distinct_resources)

        if distinct_count >= self.fanout_threshold:
            # Check cooldown: avoid spamming fanout alerts within 20s
            last_alert = self.last_fanout_alert_time[username]
            if (now - last_alert) >= 20.0:
                self.last_fanout_alert_time[username] = now

                highest_sensitivity = max(
                    (item[2] for item in recent),
                    key=lambda s: 3 if s == "TOP_SECRET" else (2 if s == "RESTRICTED" else 1),
                    default="INTERNAL"
                )
                severity = "CRITICAL" if "TOP_SECRET" in [item[2] for item in recent] else "HIGH"

                elapsed_window = int(now - recent[0][0]) + 1
                explanation = (
                    f"Graph Fan-Out Anomaly: User '{username}' accessed {distinct_count} distinct sensitive resources "
                    f"in {elapsed_window}s (Threshold: {self.fanout_threshold}). "
                    f"Resources touched: {', '.join(sorted(list(distinct_resources))[:6])}."
                )

                anomalies.append({
                    "anomaly_type": "HIGH_FANOUT",
                    "severity": severity,
                    "score": round(3.0 + (distinct_count - self.fanout_threshold) * 0.5, 2),
                    "explanation": explanation,
                    "details": {
                        "detector": "NetworkXGraphDetector",
                        "check": "FanOut",
                        "distinct_resource_count": distinct_count,
                        "threshold": self.fanout_threshold,
                        "window_seconds": self.fanout_window_seconds,
                        "resources_accessed": list(distinct_resources),
                        "highest_sensitivity": highest_sensitivity,
                    },
                })
                # Clear recent queue to reset fan-out window after alert
                recent.clear()

        return anomalies

    def get_topology(self) -> Dict[str, Any]:
        """Export current graph nodes and edges for frontend visualization."""
        nodes = []
        for n, data in self.graph.nodes(data=True):
            nodes.append({
                "id": n,
                "label": data.get("label", n),
                "type": data.get("node_type", "unknown"),
                "sensitivity": data.get("sensitivity", "NORMAL"),
            })

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "weight": data.get("weight", 1),
                "sensitivity": data.get("sensitivity", "INTERNAL"),
            })

        return {"nodes": nodes, "edges": edges}

    def reset(self):
        """Clear graph and state (for test isolation)."""
        self.graph.clear()
        self.user_resource_types.clear()
        self.user_sensitivities.clear()
        self.user_total_events.clear()
        self.user_recent_accesses.clear()
        self.last_fanout_alert_time.clear()
        self._seed_baseline_privileges()
