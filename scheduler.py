"""Background job scheduler with APScheduler."""

import asyncio
import logging
from typing import List, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import get_settings
from database.models import Article, init_database, close_database
from database.cache import alert_store
from fetcher.newsapi import fetch_newsapi
from fetcher.rss import fetch_rss
from analyzer.sentiment import analyze_articles
from analyzer.trend import process_batch

logger = logging.getLogger(__name__)
settings = get_settings()


class NewsPipeline:
    """Async news fetching and processing pipeline with content filtering."""
    
    def __init__(self):
        self.running = False
        self.noise_keywords = [kw.lower() for kw in settings.NOISE_KEYWORDS]
    
    def is_quality_content(self, title: str) -> bool:
        """Filter out noise content based on keywords in title."""
        if not title:
            return False
        
        title_lower = title.lower()
        
        # Check for noise keywords
        for keyword in self.noise_keywords:
            if keyword in title_lower:
                logger.debug(f"Filtered out (noise): '{title[:60]}...' - matched '{keyword}'")
                return False
        
        return True
    
    def filter_articles(self, articles: List[Dict]) -> List[Dict]:
        """Filter articles to keep only quality content."""
        filtered = []
        rejected = 0
        
        for article in articles:
            title = article.get("title", "")
            if self.is_quality_content(title):
                filtered.append(article)
            else:
                rejected += 1
        
        if rejected > 0:
            logger.info(f"Content filtering: {rejected} noise articles rejected, {len(filtered)} quality articles kept")
        
        return filtered
    
    async def run(self) -> None:
        """Execute full fetch-analyze-store cycle."""
        if self.running:
            logger.warning("Pipeline already running, skipping")
            return
        
        self.running = True
        logger.info("Starting news pipeline cycle...")
        
        try:
            # Fetch from all sources concurrently
            newsapi_task = fetch_newsapi()
            rss_task = fetch_rss()
            
            newsapi_articles, rss_articles = await asyncio.gather(
                newsapi_task,
                rss_task,
                return_exceptions=True,
            )
            
            # Handle exceptions
            if isinstance(newsapi_articles, Exception):
                logger.error(f"NewsAPI fetch failed: {newsapi_articles}")
                newsapi_articles = []
            
            if isinstance(rss_articles, Exception):
                logger.error(f"RSS fetch failed: {rss_articles}")
                rss_articles = []
            
            # Combine all articles
            all_articles = newsapi_articles + rss_articles
            
            if not all_articles:
                logger.warning("No articles fetched in this cycle")
                return
            
            logger.info(f"Total articles fetched: {len(all_articles)}")
            
            # Filter out noise content
            all_articles = self.filter_articles(all_articles)
            
            if not all_articles:
                logger.warning("All articles filtered out as noise")
                return
            
            logger.info(f"Quality articles after filtering: {len(all_articles)}")
            
            # Analyze sentiment
            analyzed = analyze_articles(all_articles)
            
            # Update trend engine
            process_batch(analyzed)
            
            # Store in database (with deduplication)
            stored_count = 0
            for article in analyzed:
                try:
                    result = Article.create_from_data(
                        title=article["title"],
                        source=article["source"],
                        url=article["url"],
                        sentiment=article["sentiment"],
                        category=article["category"],
                    )
                    if result:
                        stored_count += 1
                except Exception as e:
                    logger.error(f"Failed to store article: {e}")
                    continue
            
            logger.info(f"Pipeline complete: {stored_count}/{len(analyzed)} articles stored")
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
        finally:
            self.running = False


def create_scheduler() -> BackgroundScheduler:
    """Create and configure APScheduler."""
    scheduler = BackgroundScheduler()
    
    # Initialize database on startup
    init_database()
    
    pipeline = NewsPipeline()
    
    def run_pipeline_job():
        """Wrapper to safely run async pipeline in scheduler thread."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(pipeline.run())
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Scheduler job error: {e}")
    
    # Add scheduled job
    scheduler.add_job(
        run_pipeline_job,
        trigger=IntervalTrigger(seconds=settings.REFRESH_INTERVAL),
        id="news_pipeline",
        name="News Fetch Pipeline",
        replace_existing=True,
    )
    
    # Run once immediately on startup
    run_pipeline_job()
    
    return scheduler


def start_scheduler() -> BackgroundScheduler:
    """Start the background scheduler."""
    scheduler = create_scheduler()
    scheduler.start()
    logger.info(f"Scheduler started with {settings.REFRESH_INTERVAL}s interval")
    return scheduler


def stop_scheduler(scheduler: BackgroundScheduler) -> None:
    """Stop the background scheduler gracefully."""
    scheduler.shutdown(wait=True)
    close_database()
    logger.info("Scheduler stopped")
