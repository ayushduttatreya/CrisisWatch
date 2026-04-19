"""Natural language querying over stored news data (RAG-lite)."""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from services.openrouter_client import generate_text
from database.models import Article

logger = logging.getLogger(__name__)


@dataclass
class NLQueryResult:
    """Result from natural language query."""
    answer: str
    sources_used: int
    generated_at: str
    query: str
    success: bool
    error: Optional[str] = None


def _fetch_relevant_headlines(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch recent headlines from database.
    In a full RAG system, this would use vector similarity search.
    For now, we use simple keyword matching + recency.
    """
    # Get recent articles (last 24 hours worth, or just most recent)
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(hours=48)
    
    # Simple approach: fetch most recent articles
    # In production, you'd want vector similarity or full-text search
    query_lower = query.lower()
    keywords = [w for w in query_lower.split() if len(w) > 3]
    
    # Fetch recent articles
    recent_articles = (
        Article.select()
        .where(Article.fetched_at > cutoff)
        .order_by(Article.fetched_at.desc())
        .limit(50)
    )
    
    # Score articles by keyword relevance
    scored_articles = []
    for article in recent_articles:
        title_lower = article.title.lower()
        score = sum(1 for kw in keywords if kw in title_lower)
        scored_articles.append((score, article))
    
    # Sort by score (descending), then by recency
    scored_articles.sort(key=lambda x: (-x[0], x[1].fetched_at), reverse=False)
    
    # Return top matches
    top_articles = scored_articles[:max_results]
    
    return [
        {
            "title": a.title,
            "source": a.source,
            "sentiment": a.sentiment,
            "fetched_at": a.fetched_at.isoformat(),
            "url": a.url,
        }
        for _, a in top_articles
    ]


def _build_rag_prompt(query: str, headlines: List[Dict[str, Any]]) -> str:
    """Build RAG prompt with grounded headlines."""
    if not headlines:
        return f"""Answer this question about recent news:

Question: {query}

Note: No recent headlines are available in the database to answer this question.

Please inform the user that there is insufficient data to answer their question."""
    
    # Format headlines for context
    context_lines = []
    for i, h in enumerate(headlines, 1):
        sentiment_str = f"[{h['sentiment']:+.2f}]" if 'sentiment' in h else ""
        context_lines.append(f"{i}. {h['title']} ({h['source']}) {sentiment_str}")
    
    context = "\n".join(context_lines)
    
    prompt = f"""Answer the user's question using ONLY the provided headlines. Do not use outside knowledge.

Recent Headlines:
{context}

User Question: {query}

Instructions:
1. Answer based ONLY on the headlines provided above
2. If the headlines don't contain relevant information, say so clearly
3. Cite specific headlines by number when making claims
4. Keep the answer concise (2-4 sentences)
5. Mention the source publications when relevant
6. If headlines show conflicting information, acknowledge this

Answer:"""
    
    return prompt


async def query_news(
    query: str,
    max_context: int = 20,
) -> NLQueryResult:
    """
    Answer natural language query using stored news data.
    
    Args:
        query: Natural language question
        max_context: Maximum headlines to include in context
    
    Returns:
        NLQueryResult with answer and metadata
    """
    if not query or not isinstance(query, str):
        return NLQueryResult(
            answer="Invalid query provided.",
            sources_used=0,
            generated_at=datetime.utcnow().isoformat(),
            query=query or "",
            success=False,
            error="empty_query",
        )
    
    # Fetch relevant headlines
    headlines = _fetch_relevant_headlines(query, max_results=max_context)
    
    if not headlines:
        logger.warning(f"No headlines found for query: {query}")
        return NLQueryResult(
            answer="I don't have any recent news data to answer this question. The database may be empty or the query may not match available articles.",
            sources_used=0,
            generated_at=datetime.utcnow().isoformat(),
            query=query,
            success=True,  # Still a valid response
        )
    
    # Build prompt
    prompt = _build_rag_prompt(query, headlines)
    
    system_prompt = """You are a news analysis assistant. Answer questions using ONLY the provided headlines. Never hallucinate information not present in the headlines. Be factual and concise."""
    
    try:
        response = await generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=300,
            temperature=0.3,
        )
        
        if response:
            return NLQueryResult(
                answer=response.strip(),
                sources_used=len(headlines),
                generated_at=datetime.utcnow().isoformat(),
                query=query,
                success=True,
            )
        else:
            return NLQueryResult(
                answer="I was unable to generate an answer. Please try again.",
                sources_used=len(headlines),
                generated_at=datetime.utcnow().isoformat(),
                query=query,
                success=False,
                error="empty_response",
            )
    
    except Exception as e:
        logger.error(f"NL query failed: {e}")
        return NLQueryResult(
            answer="An error occurred while processing your question. Please try again later.",
            sources_used=len(headlines),
            generated_at=datetime.utcnow().isoformat(),
            query=query,
            success=False,
            error=str(e),
        )


async def summarize_topic(
    topic: str,
    hours: int = 24,
    max_headlines: int = 15,
) -> NLQueryResult:
    """
    Generate a summary of recent news on a specific topic.
    
    Args:
        topic: Topic to summarize
        hours: Lookback period in hours
        max_headlines: Maximum headlines to consider
    
    Returns:
        NLQueryResult with summary
    """
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Fetch articles containing topic keywords
    topic_lower = topic.lower()
    keywords = topic_lower.split()
    
    recent_articles = (
        Article.select()
        .where(Article.fetched_at > cutoff)
        .order_by(Article.fetched_at.desc())
        .limit(100)
    )
    
    # Filter for relevance
    relevant = []
    for article in recent_articles:
        title_lower = article.title.lower()
        if any(kw in title_lower for kw in keywords):
            relevant.append(article)
        if len(relevant) >= max_headlines:
            break
    
    if not relevant:
        return NLQueryResult(
            answer=f"No recent news found about '{topic}' in the last {hours} hours.",
            sources_used=0,
            generated_at=datetime.utcnow().isoformat(),
            query=f"Summarize: {topic}",
            success=True,
        )
    
    headlines = [
        {
            "title": a.title,
            "source": a.source,
            "sentiment": a.sentiment,
        }
        for a in relevant[:max_headlines]
    ]
    
    prompt = f"""Summarize the recent news about '{topic}' based on these headlines:

""" + "\n".join([f"- {h['title']} ({h['source']})" for h in headlines]) + """

Provide a 2-3 sentence summary of the main developments. Be factual and objective.

Summary:"""
    
    system_prompt = """You are a news summarizer. Create concise, factual summaries from headlines."""
    
    try:
        response = await generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=250,
            temperature=0.3,
        )
        
        return NLQueryResult(
            answer=response.strip() if response else f"Found {len(headlines)} articles about '{topic}' but could not generate summary.",
            sources_used=len(headlines),
            generated_at=datetime.utcnow().isoformat(),
            query=f"Summarize: {topic}",
            success=bool(response),
        )
    
    except Exception as e:
        logger.error(f"Topic summarization failed: {e}")
        return NLQueryResult(
            answer=f"Error summarizing topic: {e}",
            sources_used=len(headlines),
            generated_at=datetime.utcnow().isoformat(),
            query=f"Summarize: {topic}",
            success=False,
            error=str(e),
        )
