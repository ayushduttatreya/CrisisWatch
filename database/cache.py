"""In-memory cache for trend tracking and deduplication."""

import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TrendCache:
    """Rolling window sentiment trend cache."""
    
    def __init__(self, window_size: int = None):
        self.window_size = window_size or settings.TREND_WINDOW_SIZE
        self._values: deque = deque(maxlen=self.window_size)
        self._timestamps: deque = deque(maxlen=self.window_size)
    
    def add(self, sentiment: float, timestamp: Optional[datetime] = None) -> None:
        """Add sentiment value to rolling window."""
        self._values.append(sentiment)
        self._timestamps.append(timestamp or datetime.utcnow())
    
    def get_average(self) -> float:
        """Calculate average sentiment in window."""
        if not self._values:
            return 0.0
        return sum(self._values) / len(self._values)
    
    def get_trend(self) -> List[float]:
        """Get trend values as list."""
        return list(self._values)
    
    def is_spike(self, threshold: float = None) -> bool:
        """Detect crisis spike when average sentiment drops below threshold."""
        if len(self._values) < 10:  # Need minimum data
            return False
        threshold = threshold or settings.SPIKE_THRESHOLD
        return self.get_average() < threshold


class AlertStore:
    """Store for crisis alerts."""
    
    def __init__(self, max_alerts: int = 50):
        self._alerts: deque = deque(maxlen=max_alerts)
    
    def add_alert(self, alert_type: str, message: str) -> Dict:
        """Add new alert."""
        alert = {
            "type": alert_type,
            "msg": message,
            "time": datetime.utcnow().isoformat(),
        }
        self._alerts.append(alert)
        return alert
    
    def get_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts."""
        return list(self._alerts)[-limit:]
    
    def clear(self) -> None:
        """Clear all alerts."""
        self._alerts.clear()


# Global cache instances
trend_cache = TrendCache()
alert_store = AlertStore()


def get_cache_stats() -> Dict:
    """Get current cache statistics."""
    return {
        "trend_points": len(trend_cache.get_trend()),
        "average_sentiment": trend_cache.get_average(),
        "is_spike": trend_cache.is_spike(),
        "alerts_count": len(alert_store.get_alerts(100)),
    }
