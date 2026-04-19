"""Async NewsAPI fetcher using httpx."""

import logging
from typing import Dict, List, Any

from datetime import datetime, timedelta, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NewsAPIFetcher:
    """Async fetcher for NewsAPI with proper error handling."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.NEWS_API_KEY
        self.base_url = settings.NEWS_API_URL
        self.timeout = 30.0
    
    async def fetch_category(
        self,
        client: httpx.AsyncClient,
        category: str,
        page_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """Fetch headlines for a single category."""
        if not self.api_key:
            logger.warning("No NEWS_API_KEY configured, skipping NewsAPI fetch")
            return []
        
        params = {
            "apiKey": self.api_key,
            "category": category,
            "pageSize": page_size,
            "language": "en",
        }
        
        try:
            response = await client.get(
                self.base_url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "ok":
                logger.error(f"NewsAPI error for {category}: {data}")
                return []
            
            articles = []
            discarded = 0
            cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
            
            for item in data.get("articles", []):
                if not item.get("title") or not item.get("url"):
                    continue
                    
                pub_date = None
                pub_str = item.get("publishedAt")
                if pub_str:
                    try:
                        pub_date = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
                        if pub_date.tzinfo is None:
                            pub_date = pub_date.replace(tzinfo=timezone.utc)
                    except ValueError:
                        pub_date = datetime.now(timezone.utc)
                else:
                    pub_date = datetime.now(timezone.utc)
                    
                if pub_date < cutoff:
                    discarded += 1
                    logger.debug(f"Discarded outdated article: {item['title'][:50]}...")
                    continue
                    
                articles.append({
                    "title": item["title"].strip(),
                    "source": item.get("source", {}).get("name", "NewsAPI"),
                    "url": item["url"],
                    "category": category,
                    "published_at": pub_date.isoformat(),
                })
            
            logger.info(f"Fetched {len(articles)} articles from NewsAPI category: {category} (Discarded {discarded} outdated)")
            return articles
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {category}: {e.response.status_code}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Request error fetching {category}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching {category}: {e}")
            return []
    
    async def fetch_all(self) -> List[Dict[str, Any]]:
        """Fetch all categories concurrently."""
        if not self.api_key:
            return []
        
        categories = settings.NEWS_CATEGORIES
        all_articles = []
        
        async with httpx.AsyncClient() as client:
            tasks = [
                self.fetch_category(client, cat)
                for cat in categories
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Category fetch failed: {result}")
                continue
            all_articles.extend(result)
        
        logger.info(f"NewsAPI total articles fetched: {len(all_articles)}")
        return all_articles


async def fetch_newsapi() -> List[Dict[str, Any]]:
    """Convenience function to fetch from NewsAPI."""
    fetcher = NewsAPIFetcher()
    return await fetcher.fetch_all()


# Import asyncio here to avoid issues with module loading
import asyncio
