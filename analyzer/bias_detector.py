"""AI-powered political and media bias detection for news headlines."""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import asyncio

from services.openrouter_client import generate_json

logger = logging.getLogger(__name__)


class BiasLabel(str, Enum):
    """Bias classification labels."""
    LEFT = "left"
    RIGHT = "right"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


@dataclass
class BiasResult:
    """Structured bias detection result."""
    bias: str
    confidence: float
    explanation: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "bias": self.bias,
            "bias_confidence": round(self.confidence, 3),
        }


# Keywords that may indicate bias direction (fallback method)
LEFT_INDICATORS = {
    "progressive", "liberal", "socialist", "left-wing", "activist",
    "workers", "labor", "union", "equality", "social justice",
    "reform", "change", "grassroots", "protest", "demonstration",
    "climate action", "green new deal", "healthcare for all",
    "tax the rich", "wealth tax", "income inequality",
    "lgbtq rights", "abortion rights", "reproductive rights",
    "gun control", "immigration reform", "path to citizenship",
    "minimum wage", "living wage", "paid leave",
    "regulation", "oversight", "accountability",
    "corporate greed", "wall street", "big banks",
    "universal basic income", "ubi",
}

RIGHT_INDICATORS = {
    "conservative", "traditional", "free market", "deregulation",
    "tax cuts", "lower taxes", "small government", "states rights",
    "second amendment", "gun rights", "pro-life", "pro life",
    "border security", "illegal immigration", "national security",
    "strong military", "defense spending", "patriot", "patriotic",
    "religious freedom", "faith-based", "family values",
    "school choice", "vouchers", "merit-based",
    "energy independence", "drill baby drill", "keystone",
    "america first", "make america great", "maga",
    "cancel culture", "woke", "politically correct", "pc culture",
    "mainstream media", "fake news", "liberal media",
    "big government", "government overreach", "nanny state",
    "personal responsibility", "bootstraps", "self-reliance",
    "entitlement reform", "welfare reform", "work requirements",
    "law and order", "tough on crime", "back the blue",
    "antifa", "radical left", "socialism", "communism",
}

EMOTIONAL_INDICATORS = {
    "outrage", "shocking", "devastating", "disastrous", "catastrophic",
    "terrifying", "horrifying", "unbelievable", "incredible",
    "must read", "urgent", "breaking", "alert", "warning",
    "slams", "blasts", "destroys", "crushes", "eviscerates",
    "perfect", "beautiful", "tremendous", "huge", "massive",
    "epic", "fail", "win", "owned", "destroyed",
}


def _fallback_bias_detection(headline: str) -> BiasResult:
    """Fallback bias detection using keyword heuristics."""
    headline_lower = headline.lower()
    
    left_score = sum(1 for word in LEFT_INDICATORS if word in headline_lower)
    right_score = sum(1 for word in RIGHT_INDICATORS if word in headline_lower)
    emotional_score = sum(1 for word in EMOTIONAL_INDICATORS if word in headline_lower)
    
    # Calculate confidence based on keyword density
    words = headline_lower.split()
    total_words = len(words) if words else 1
    
    if left_score > right_score:
        confidence = min(0.5 + (left_score / total_words), 0.8)
        return BiasResult(bias=BiasLabel.LEFT, confidence=round(confidence, 3))
    elif right_score > left_score:
        confidence = min(0.5 + (right_score / total_words), 0.8)
        return BiasResult(bias=BiasLabel.RIGHT, confidence=round(confidence, 3))
    elif emotional_score > 0:
        # Emotional language but no clear political indicators
        confidence = min(0.3 + (emotional_score / total_words), 0.6)
        return BiasResult(bias=BiasLabel.NEUTRAL, confidence=round(confidence, 3))
    else:
        return BiasResult(bias=BiasLabel.NEUTRAL, confidence=0.7)


def _build_bias_prompt(headline: str, source: Optional[str] = None) -> str:
    """Build prompt for bias detection."""
    source_context = f"\nSource: {source}" if source else ""
    
    prompt = f"""Analyze the political/media bias in this news headline.{source_context}

Headline: "{headline}"

Classify the bias and provide confidence score.

Consider:
- Loaded or emotional language
- Framing that favors one political side
- Omission of context that would change interpretation
- Source reputation (if known)

Return ONLY a JSON object:
{{
    "bias": "left" | "right" | "neutral",
    "confidence": 0.0 to 1.0,
    "explanation": "brief reason for classification"
}}

Guidelines:
- "left": Language favoring progressive/liberal viewpoints
- "right": Language favoring conservative viewpoints  
- "neutral": Balanced reporting, factual presentation
- Confidence: 0.9+ = very clear bias, 0.7-0.9 = moderate bias, 0.5-0.7 = slight lean, <0.5 = uncertain

JSON output:"""
    
    return prompt


async def detect_bias(
    headline: str,
    source: Optional[str] = None,
    use_fallback: bool = True,
) -> BiasResult:
    """
    Detect political/media bias in a headline.
    
    Args:
        headline: News headline text
        source: Optional source name for context
        use_fallback: Use keyword fallback if AI fails
    
    Returns:
        BiasResult with classification and confidence
    """
    if not headline or not isinstance(headline, str):
        return BiasResult(bias=BiasLabel.UNKNOWN, confidence=0.0)
    
    prompt = _build_bias_prompt(headline, source)
    
    system_prompt = """You are an objective media bias analyst. Analyze headlines for political leanings based on language choice, framing, and tone. Be impartial and consistent. Return valid JSON only."""
    
    try:
        result = await generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=150,
            temperature=0.2,
        )
        
        if result:
            bias = result.get("bias", BiasLabel.NEUTRAL).lower()
            confidence = float(result.get("confidence", 0.5))
            
            # Validate bias label
            if bias not in [b.value for b in BiasLabel]:
                bias = BiasLabel.NEUTRAL
            
            # Clamp confidence
            confidence = max(0.0, min(1.0, confidence))
            
            return BiasResult(
                bias=bias,
                confidence=round(confidence, 3),
                explanation=result.get("explanation"),
            )
        
    except Exception as e:
        logger.error(f"Bias detection failed for '{headline[:50]}...': {e}")
    
    # Fallback
    if use_fallback:
        return _fallback_bias_detection(headline)
    
    return BiasResult(bias=BiasLabel.UNKNOWN, confidence=0.0)


async def detect_bias_batch(
    items: List[tuple[str, Optional[str]]],
    max_concurrent: int = 5,
) -> List[BiasResult]:
    """
    Detect bias for multiple headlines with concurrency control.
    
    Args:
        items: List of (headline, source) tuples
        max_concurrent: Maximum concurrent detections
    
    Returns:
        List of BiasResult objects
    """
    if not items:
        return []
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def detect_with_limit(headline: str, source: Optional[str]) -> BiasResult:
        async with semaphore:
            return await detect_bias(headline, source)
    
    tasks = [detect_with_limit(h, s) for h, s in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions gracefully
    processed_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Batch bias detection error: {result}")
            processed_results.append(BiasResult(bias=BiasLabel.UNKNOWN, confidence=0.0))
        else:
            processed_results.append(result)
    
    return processed_results


def get_bias_color(bias: str) -> str:
    """Get color code for bias indicator."""
    colors = {
        BiasLabel.LEFT: "#3b82f6",      # Blue
        BiasLabel.RIGHT: "#ef4444",     # Red
        BiasLabel.NEUTRAL: "#22c55e",   # Green
        BiasLabel.UNKNOWN: "#94a3b8",   # Gray
    }
    return colors.get(bias, "#94a3b8")


def get_bias_emoji(bias: str) -> str:
    """Get emoji indicator for bias."""
    emojis = {
        BiasLabel.LEFT: "←",
        BiasLabel.RIGHT: "→",
        BiasLabel.NEUTRAL: "◆",
        BiasLabel.UNKNOWN: "?",
    }
    return emojis.get(bias, "?")
