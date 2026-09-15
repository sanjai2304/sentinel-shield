"""Rolling statistical Z-Score anomaly detector for user-resource access frequency."""
import time
import math
from collections import deque, defaultdict
from typing import Dict, List, Tuple, Optional, Any
from app.config import settings


class RollingZScoreDetector:
    """Detects frequency/volumetric anomalies in user access patterns using rolling Z-scores.

    Maintains sliding micro-windows of access event timestamps per (username, resource_key)
    and keeps rolling historical baseline distributions (mean and standard deviation).
    """

    def __init__(
        self,
        window_seconds: int = settings.Z_SCORE_WINDOW_SECONDS,
        threshold: float = 3.5,
        min_events: int = 6,
        min_rate_threshold: int = 14,  # Minimum requests in window before flagging an exfiltration spike
    ):
        self.window_seconds = window_seconds
        self.threshold = threshold
        self.min_events = min_events
        self.min_rate_threshold = min_rate_threshold
        
        # Recent sliding event timestamps: key -> deque([t1, t2, ...])
        self.recent_windows: Dict[str, deque] = defaultdict(deque)

        # Historical window frequency samples: key -> deque([rate1, rate2, ...])
        self.history_samples: Dict[str, deque] = defaultdict(lambda: deque(maxlen=60))
        self.last_sample_time: Dict[str, float] = defaultdict(float)

        # Alert throttling: key -> (last_alert_time, last_alert_rate)
        self.last_alert_info: Dict[str, Tuple[float, int]] = defaultdict(lambda: (0.0, 0))

    def _get_key(self, username: str, resource_key: str) -> str:
        return f"{username}:{resource_key}"

    def process_event(
        self,
        username: str,
        resource_key: str,
        event_time: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Process an incoming access event and evaluate whether it constitutes a Z-score anomaly.

        Returns anomaly dictionary if flagged, or None if within normal parameters.
        """
        now = event_time if event_time is not None else time.time()
        key = self._get_key(username, resource_key)

        # 1. Prune timestamps outside the sliding window
        window = self.recent_windows[key]
        cutoff = now - self.window_seconds
        while window and window[0] < cutoff:
            window.popleft()

        # Add current event timestamp
        window.append(now)
        current_rate = len(window)

        # 2. Record historical samples periodically (every 10 seconds)
        history = self.history_samples[key]
        last_sampled = self.last_sample_time[key]
        if (now - last_sampled) >= 10.0 or len(history) < self.min_events:
            # We record counts only when window has a baseline observation
            history.append(current_rate)
            self.last_sample_time[key] = now

        # Need minimum history samples before evaluating
        if len(history) < self.min_events:
            return None

        # 3. Calculate mean and standard deviation of historical rates
        mean = sum(history) / len(history)
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        std_dev = math.sqrt(variance)

        # Natural access variance floor: normal human browsing fluctuates by ±2.5 req/min
        effective_std = max(std_dev, 2.5)
        z_score = (current_rate - mean) / effective_std

        # 4. Check if:
        #    a) Z-Score exceeds threshold (>= 3.5 sigma)
        #    b) Absolute request count exceeds the min rate threshold (>= 14 req/min)
        #    c) Rate is substantially above mean (at least +6 above mean)
        if z_score >= self.threshold and current_rate >= self.min_rate_threshold and current_rate >= (mean + 5):
            # Cooldown check: avoid spamming 10 identical alerts for the same ongoing burst
            last_alert_time, last_alert_rate = self.last_alert_info[key]
            if (now - last_alert_time) < 15.0 and current_rate < (last_alert_rate + 6):
                return None  # Cooldown active for this burst

            self.last_alert_info[key] = (now, current_rate)

            # Determine severity based on sigma divergence
            if z_score >= 6.0:
                severity = "CRITICAL"
            elif z_score >= 4.5:
                severity = "HIGH"
            elif z_score >= 3.5:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            explanation = (
                f"Statistical Rate Anomaly (Z-Score: {z_score:.2f}): User '{username}' executed "
                f"{current_rate} requests within {self.window_seconds}s to '{resource_key}'. "
                f"Historical baseline is {mean:.1f} ± {std_dev:.1f} req/{self.window_seconds}s."
            )

            return {
                "anomaly_type": "FREQUENCY_ZSCORE",
                "severity": severity,
                "score": round(z_score, 2),
                "explanation": explanation,
                "details": {
                    "detector": "RollingZScore",
                    "current_rate_in_window": current_rate,
                    "window_seconds": self.window_seconds,
                    "baseline_mean": round(mean, 2),
                    "baseline_std": round(std_dev, 2),
                    "z_score": round(z_score, 2),
                    "sample_count": len(history),
                },
            }

        return None

    def reset(self):
        """Reset internal sliding windows and history (useful for tests)."""
        self.recent_windows.clear()
        self.history_samples.clear()
        self.last_sample_time.clear()
        self.last_alert_info.clear()
