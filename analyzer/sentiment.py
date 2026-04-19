"""VADER sentiment analysis engine."""

import logging
from typing import Dict, List, Any

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """VADER-based sentiment analyzer for news headlines."""
    
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
    
    def analyze(self, text: str) -> float:
        """
        Analyze sentiment of text and return compound score.
        Returns score between -1 (very negative) and +1 (very positive).
        """
        if not text or not isinstance(text, str):
            return 0.0
        
        scores = self.analyzer.polarity_scores(text)
        return scores["compound"]
    
    def analyze_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment of a single article."""
        title = article.get("title", "")
        sentiment = self.analyze(title)
        
        return {
            "title": article["title"],
            "source": article["source"],
            "url": article["url"],
            "category": article.get("category", "general"),
            "sentiment": sentiment,
        }
    
    def analyze_batch(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze sentiment for a batch of articles."""
        results = []
        
        for article in articles:
            try:
                analyzed = self.analyze_article(article)
                results.append(analyzed)
            except Exception as e:
                logger.error(f"Failed to analyze article '{article.get('title', 'unknown')}': {e}")
                continue
        
        logger.info(f"Analyzed sentiment for {len(results)} articles")
        return results
    
    def classify(self, score: float) -> str:
        """Classify sentiment score into category."""
        if score >= 0.05:
            return "positive"
        elif score <= -0.05:
            return "negative"
        return "neutral"


# Global analyzer instance
_sentiment_analyzer: SentimentAnalyzer = None


def get_analyzer() -> SentimentAnalyzer:
    """Get or create sentiment analyzer singleton."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer


def analyze_text(text: str) -> float:
    """Convenience function to analyze text sentiment."""
    return get_analyzer().analyze(text)


def analyze_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convenience function to analyze batch of articles."""
    return get_analyzer().analyze_batch(articles)
