"""AI-powered crisis summary generation when sentiment spikes occur."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from services.openrouter_client import generate_text, AIResponse

logger = logging.getLogger(__name__)


@dataclass
class CrisisSummary:
    """Structured crisis summary with metadata."""
    summary: str
    generated_at: str
    headline_count: int
    avg_sentiment: float
    model: str = "openrouter"
    cached: bool = False


# In-memory cache for summaries to avoid regenerating during active spikes
_summary_cache: Dict[str, CrisisSummary] = {}


def _build_summary_prompt(headlines: List[str], avg_sentiment: float) -> str:
    """Build prompt for crisis summary generation."""
    headline_list = "\n".join([f"- {h}" for h in headlines])
    
    prompt = f"""Analyze these negative news headlines and provide a concise 2-3 sentence geopolitical summary.

Headlines (average sentiment: {avg_sentiment:.3f}):
{headline_list}

Requirements:
- Identify the main crisis or event causing negative sentiment
- Mention specific countries, regions, or entities involved
- Explain the potential geopolitical impact
- Be factual and avoid speculation beyond what's in the headlines
- Keep to 2-3 sentences maximum

Summary:"""
    
    return prompt


async def generate_crisis_summary(
    headlines: List[str],
    avg_sentiment: float,
    force_refresh: bool = False,
) -> Optional[CrisisSummary]:
    """
    Generate AI crisis summary from negative headlines.
    
    Args:
        headlines: List of negative headlines (top 5-10)
        avg_sentiment: Average sentiment score for context
        force_refresh: Force regeneration even if cached
    
    Returns:
        CrisisSummary object or None if generation fails
    """
    if not headlines:
        logger.warning("No headlines provided for summary generation")
        return None
    
    # Create cache key from headline signatures
    cache_key = f"spike:{hash(''.join(headlines[:5]))}"
    
    # Check cache unless force refresh
    if not force_refresh and cache_key in _summary_cache:
        cached = _summary_cache[cache_key]
        # Cache valid for 5 minutes during active spike
        generated_time = datetime.fromisoformat(cached.generated_at)
        if (datetime.utcnow() - generated_time).seconds < 300:
            logger.info("Using cached crisis summary")
            return CrisisSummary(
                summary=cached.summary,
                generated_at=cached.generated_at,
                headline_count=cached.headline_count,
                avg_sentiment=cached.avg_sentiment,
                cached=True,
            )
    
    # Build prompt
    prompt = _build_summary_prompt(headlines, avg_sentiment)
    
    system_prompt = """You are a geopolitical intelligence analyst. Provide concise, factual summaries of crisis events based on news headlines. Focus on identifying key actors, regions, and potential impacts. Avoid sensationalism."""
    
    # Generate summary
    response = await generate_text(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=200,
        temperature=0.3,
    )
    
    if not response:
        logger.error("Failed to generate crisis summary")
        return None
    
    # Clean up response
    summary_text = response.strip()
    
    # Create summary object
    summary = CrisisSummary(
        summary=summary_text,
        generated_at=datetime.utcnow().isoformat(),
        headline_count=len(headlines),
        avg_sentiment=avg_sentiment,
        cached=False,
    )
    
    # Cache result
    _summary_cache[cache_key] = summary
    
    logger.info(f"Generated crisis summary from {len(headlines)} headlines")
    return summary


async def get_summary_for_spike(
    recent_articles: List[Dict[str, Any]],
    spike_threshold: float = -0.3,
) -> Optional[CrisisSummary]:
    """
    Get crisis summary for detected spike using most negative articles.
    
    Args:
        recent_articles: List of recent article dictionaries
        spike_threshold: Sentiment threshold for "negative" articles
    
    Returns:
        CrisisSummary or None
    """
    # Filter to most negative headlines
    negative_articles = [
        a for a in recent_articles 
        if a.get("sentiment", 0) < spike_threshold
    ]
    
    if not negative_articles:
        logger.info("No sufficiently negative articles for crisis summary")
        return None
    
    # Sort by sentiment (most negative first)
    negative_articles.sort(key=lambda x: x.get("sentiment", 0))
    
    # Take top 5-10 most negative
    top_negative = negative_articles[:10]
    headlines = [a.get("title", "") for a in top_negative if a.get("title")]
    
    if not headlines:
        return None
    
    # Calculate average sentiment
    avg_sentiment = sum(a.get("sentiment", 0) for a in top_negative) / len(top_negative)
    
    return await generate_crisis_summary(headlines, avg_sentiment)


def clear_summary_cache() -> None:
    """Clear the summary cache (useful for testing)."""
    global _summary_cache
    _summary_cache.clear()
    logger.info("Cleared summary cache")
