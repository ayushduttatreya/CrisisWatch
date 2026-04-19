"""Tests for sentiment analysis engine."""

import pytest
from unittest.mock import patch, MagicMock

from analyzer.sentiment import SentimentAnalyzer, analyze_text, analyze_articles


class TestSentimentAnalyzer:
    """Test cases for SentimentAnalyzer."""
    
    def test_analyze_positive(self):
        """Test positive sentiment detection."""
        analyzer = SentimentAnalyzer()
        
        text = "Great news! The economy is booming and markets are up."
        score = analyzer.analyze(text)
        
        assert score > 0.05
        assert -1 <= score <= 1
    
    def test_analyze_negative(self):
        """Test negative sentiment detection."""
        analyzer = SentimentAnalyzer()
        
        text = "Terrible tragedy! Crisis deepens as conflict escalates violently."
        score = analyzer.analyze(text)
        
        assert score < -0.05
        assert -1 <= score <= 1
    
    def test_analyze_neutral(self):
        """Test neutral sentiment detection."""
        analyzer = SentimentAnalyzer()
        
        text = "The meeting will be held at 3 PM today."
        score = analyzer.analyze(text)
        
        assert -0.05 <= score <= 0.05
    
    def test_analyze_empty(self):
        """Test handling of empty text."""
        analyzer = SentimentAnalyzer()
        
        score = analyzer.analyze("")
        assert score == 0.0
        
        score = analyzer.analyze(None)
        assert score == 0.0
    
    def test_classify(self):
        """Test sentiment classification."""
        analyzer = SentimentAnalyzer()
        
        assert analyzer.classify(0.5) == "positive"
        assert analyzer.classify(0.05) == "positive"
        assert analyzer.classify(-0.5) == "negative"
        assert analyzer.classify(-0.05) == "negative"
        assert analyzer.classify(0.0) == "neutral"
        assert analyzer.classify(0.04) == "neutral"
        assert analyzer.classify(-0.04) == "neutral"
    
    def test_analyze_article(self):
        """Test single article analysis."""
        analyzer = SentimentAnalyzer()
        
        article = {
            "title": "Breaking: Major breakthrough in peace talks",
            "source": "Reuters",
            "url": "https://example.com/news",
            "category": "world"
        }
        
        result = analyzer.analyze_article(article)
        
        assert "title" in result
        assert "sentiment" in result
        assert result["title"] == article["title"]
        assert result["source"] == article["source"]
        assert isinstance(result["sentiment"], float)
    
    def test_analyze_batch(self):
        """Test batch article analysis."""
        analyzer = SentimentAnalyzer()
        
        articles = [
            {
                "title": "Markets crash amid global uncertainty",
                "source": "Bloomberg",
                "url": "https://example.com/1",
            },
            {
                "title": "New innovation promises bright future",
                "source": "TechCrunch",
                "url": "https://example.com/2",
            },
        ]
        
        results = analyzer.analyze_batch(articles)
        
        assert len(results) == 2
        assert all("sentiment" in r for r in results)
        assert all(isinstance(r["sentiment"], float) for r in results)
    
    def test_analyze_batch_with_errors(self):
        """Test batch analysis handles individual failures."""
        analyzer = SentimentAnalyzer()
        
        articles = [
            {
                "title": "Valid headline",
                "source": "Test",
                "url": "https://example.com/1",
            },
            {
                # Missing title should be handled gracefully
                "source": "Test",
                "url": "https://example.com/2",
            },
        ]
        
        results = analyzer.analyze_batch(articles)
        
        assert len(results) >= 1  # At least one processed
    
    def test_singleton_get_analyzer(self):
        """Test analyzer singleton pattern."""
        from analyzer.sentiment import get_analyzer
        
        a1 = get_analyzer()
        a2 = get_analyzer()
        
        assert a1 is a2
    
    def test_convenience_analyze_text(self):
        """Test convenience function."""
        score = analyze_text("Amazing positive news today!")
        assert score > 0
        assert -1 <= score <= 1
    
    def test_convenience_analyze_articles(self):
        """Test convenience batch function."""
        articles = [
            {"title": "Test 1", "source": "Test", "url": "https://test.com/1"},
            {"title": "Test 2", "source": "Test", "url": "https://test.com/2"},
        ]
        
        results = analyze_articles(articles)
        assert len(results) == 2


class TestSentimentWithMocking:
    """Test cases with mocked VADER."""
    
    @patch('analyzer.sentiment.SentimentIntensityAnalyzer')
    def test_mocked_analyzer(self, mock_analyzer_class):
        """Test with mocked VADER analyzer."""
        mock_instance = MagicMock()
        mock_instance.polarity_scores.return_value = {"compound": 0.75}
        mock_analyzer_class.return_value = mock_instance
        
        analyzer = SentimentAnalyzer()
        score = analyzer.analyze("Test text")
        
        assert score == 0.75
        mock_instance.polarity_scores.assert_called_once_with("Test text")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
