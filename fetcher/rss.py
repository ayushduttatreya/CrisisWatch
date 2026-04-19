"""RSS feed fetcher using feedparser."""

import logging
from typing import Dict, List, Any
from urllib.parse import urlparse

import feedparser
import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RSSFetcher:
    """RSS feed fetcher with HTTP fallback for feedparser."""
    
    def __init__(self, feeds: List[str] = None):
        self.feeds = feeds or settings.RSS_FEEDS
        self.timeout = 30.0
    
    async def fetch_feed(self, url: str) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed."""
        articles = []
        
        try:
            # Use httpx to fetch feed content
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=self.timeout, follow_redirects=True)
                response.raise_for_status()
                content = response.content
            
            # Parse with feedparser
            feed = feedparser.parse(content)
            
            if feed.get("bozo"):
                logger.warning(f"Feed parsing warning for {url}: {feed.get('bozo_exception', 'Unknown')}")
            
            source_name = self._extract_source_name(feed, url)
            
            for entry in feed.get("entries", []):
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                
                if not title or not link:
                    continue
                
                articles.append({
                    "title": title,
                    "source": source_name,
                    "url": link,
                    "category": "general",
                })
            
            logger.info(f"Fetched {len(articles)} articles from RSS: {source_name}")
            return articles
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching RSS {url}: {e.response.status_code}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Request error fetching RSS {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching RSS {url}: {e}")
            return []
    
    def _extract_source_name(self, feed: Any, url: str) -> str:
        """Extract source name from feed metadata."""
        # Try feed title
        if feed.get("feed", {}).get("title"):
            return feed["feed"]["title"][:50]
        
        # Fall back to domain
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain or "RSS Feed"
    
    async def fetch_all(self) -> List[Dict[str, Any]]:
        """Fetch all RSS feeds concurrently."""
        import asyncio
        
        all_articles = []
        
        tasks = [
            self.fetch_feed(url)
            for url in self.feeds
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"RSS fetch failed: {result}")
                continue
            all_articles.extend(result)
        
        logger.info(f"RSS total articles fetched: {len(all_articles)}")
        return all_articles


async def fetch_rss() -> List[Dict[str, Any]]:
    """Convenience function to fetch from RSS feeds."""
    fetcher = RSSFetcher()
    return await fetcher.fetch_all()
