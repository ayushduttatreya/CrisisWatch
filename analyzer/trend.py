"""Trend analysis engine for sentiment tracking."""

import logging
from datetime import datetime
from typing import Dict, List

from database.cache import alert_store, trend_cache
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TrendEngine:
    """Engine for tracking sentiment trends and detecting spikes."""
    
    def __init__(self):
        self.spike_threshold = settings.SPIKE_THRESHOLD
        self.spike_active = False
    
    def process_articles(self, articles: List[Dict]) -> None:
        """Process batch of articles and update trend data."""
        if not articles:
            return
        
        # Calculate average sentiment for this batch
        sentiments = [a["sentiment"] for a in articles if "sentiment" in a]
        if not sentiments:
            return
        
        batch_average = sum(sentiments) / len(sentiments)
        
        # Add to rolling window
        trend_cache.add(batch_average)
        
        # Check for spike
        self._check_spike(batch_average)
        
        logger.info(
            f"Trend updated: batch_avg={batch_average:.3f}, "
            f"window_avg={trend_cache.get_average():.3f}, "
            f"points={len(trend_cache.get_trend())}"
        )
    
    def _check_spike(self, batch_average: float) -> None:
        """Check if crisis spike is detected."""
        window_avg = trend_cache.get_average()
        is_spike = trend_cache.is_spike(self.spike_threshold)
        
        if is_spike and not self.spike_active:
            # Spike just started
            self.spike_active = True
            alert = alert_store.add_alert(
                "crisis",
                f"Negative sentiment spike detected (avg: {window_avg:.3f})"
            )
            logger.warning(f"Crisis spike detected: {alert}")
            
        elif not is_spike and self.spike_active:
            # Spike ended
            self.spike_active = False
            alert_store.add_alert(
                "info",
                f"Sentiment returning to normal (avg: {window_avg:.3f})"
            )
            logger.info("Crisis spike ended")
    
    def get_trend_data(self) -> List[float]:
        """Get current trend values."""
        return trend_cache.get_trend()
    
    def get_stats(self) -> Dict:
        """Get current trend statistics."""
        trend = trend_cache.get_trend()
        
        return {
            "trend_points": len(trend),
            "average_sentiment": trend_cache.get_average(),
            "is_spike": trend_cache.is_spike(),
            "current_spike": self.spike_active,
            "latest_value": trend[-1] if trend else 0.0,
        }


# Global engine instance
_trend_engine: TrendEngine = None


def get_engine() -> TrendEngine:
    """Get or create trend engine singleton."""
    global _trend_engine
    if _trend_engine is None:
        _trend_engine = TrendEngine()
    return _trend_engine


def process_batch(articles: List[Dict]) -> None:
    """Convenience function to process article batch."""
    get_engine().process_articles(articles)


def get_trend() -> List[float]:
    """Convenience function to get trend data."""
    return trend_cache.get_trend()


def get_current_stats() -> Dict:
    """Get current trend and sentiment statistics."""
    return {
        **get_engine().get_stats(),
        "alerts": alert_store.get_alerts(10),
    }
