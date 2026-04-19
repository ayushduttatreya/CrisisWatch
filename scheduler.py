"""Background job scheduler with APScheduler."""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import get_settings
from database.models import Article, AISummary, init_database, close_database
from database.cache import alert_store, trend_cache
from fetcher.newsapi import fetch_newsapi
from fetcher.rss import fetch_rss
from analyzer.sentiment import analyze_articles
from analyzer.trend import process_batch, get_engine
from analyzer.entity_extractor import extract_entities_batch, aggregate_entities
from analyzer.bias_detector import detect_bias_batch
from analyzer.ai_summary import generate_crisis_summary

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
            stored_articles = []  # Track stored articles for AI processing
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
                        stored_articles.append({
                            "id": result.id,
                            "title": result.title,
                            "source": result.source,
                            "sentiment": result.sentiment,
                            "url": result.url,
                        })
                except Exception as e:
                    logger.error(f"Failed to store article: {e}")
                    continue
            
            logger.info(f"Pipeline complete: {stored_count}/{len(analyzed)} articles stored")
            
            # Queue AI enrichment tasks (non-blocking)
            if settings.AI_ENABLED and stored_articles:
                asyncio.create_task(self._run_ai_enrichment(stored_articles))
            
            # Generate crisis summary if spike detected
            if settings.AI_CRISIS_SUMMARY and trend_cache.is_spike():
                asyncio.create_task(self._generate_crisis_summary_if_needed())
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
        finally:
            self.running = False
    
    async def _run_ai_enrichment(self, articles: List[Dict[str, Any]]) -> None:
        """
        Run AI enrichment tasks asynchronously without blocking.
        Processes: entity extraction, bias detection
        """
        if not articles:
            return
        
        logger.info(f"Starting AI enrichment for {len(articles)} articles")
        
        try:
            # Extract entities if enabled
            if settings.AI_ENTITY_EXTRACTION:
                await self._enrich_entities(articles)
            
            # Detect bias if enabled
            if settings.AI_BIAS_DETECTION:
                await self._enrich_bias(articles)
                
        except Exception as e:
            logger.error(f"AI enrichment error: {e}")
    
    async def _enrich_entities(self, articles: List[Dict[str, Any]]) -> None:
        """Extract and store entities for articles."""
        try:
            headlines = [a["title"] for a in articles]
            entities_list = await extract_entities_batch(headlines, max_concurrent=3)
            
            # Store results
            for article, entities in zip(articles, entities_list):
                if not entities.is_empty():
                    try:
                        db_article = Article.get_by_id(article["id"])
                        db_article.set_entities(entities.to_dict())
                        db_article.save()
                    except Exception as e:
                        logger.error(f"Failed to save entities for article {article['id']}: {e}")
            
            logger.info(f"Entity extraction complete for {len(articles)} articles")
            
        except Exception as e:
            logger.error(f"Entity enrichment error: {e}")
    
    async def _enrich_bias(self, articles: List[Dict[str, Any]]) -> None:
        """Detect and store bias for articles."""
        try:
            items = [(a["title"], a.get("source")) for a in articles]
            bias_results = await detect_bias_batch(items, max_concurrent=3)
            
            # Store results
            for article, bias in zip(articles, bias_results):
                try:
                    db_article = Article.get_by_id(article["id"])
                    db_article.set_bias(bias.bias, bias.confidence)
                    db_article.save()
                except Exception as e:
                    logger.error(f"Failed to save bias for article {article['id']}: {e}")
            
            logger.info(f"Bias detection complete for {len(articles)} articles")
            
        except Exception as e:
            logger.error(f"Bias enrichment error: {e}")
    
    async def _generate_crisis_summary_if_needed(self) -> None:
        """Generate crisis summary when spike is detected."""
        try:
            # Check if we already have a recent summary
            latest = AISummary.get_latest_crisis_summary()
            if latest:
                generated_time = datetime.fromisoformat(latest.generated_at)
                if (datetime.utcnow() - generated_time).seconds < 300:  # 5 min cache
                    logger.info("Using existing crisis summary (within 5min cache)")
                    return
            
            # Get most negative recent articles
            negative_articles = (
                Article.select()
                .where(Article.sentiment < settings.SPIKE_THRESHOLD)
                .order_by(Article.fetched_at.desc())
                .limit(10)
            )
            
            if not negative_articles:
                return
            
            # Sort by sentiment (most negative first)
            negative_list = list(negative_articles)
            negative_list.sort(key=lambda x: x.sentiment)
            
            headlines = [a.title for a in negative_list[:10]]
            avg_sentiment = sum(a.sentiment for a in negative_list) / len(negative_list)
            
            # Generate summary
            summary = await generate_crisis_summary(headlines, avg_sentiment)
            
            if summary:
                # Store in database
                AISummary.create(
                    summary_type="crisis",
                    content=summary.summary,
                    headline_count=summary.headline_count,
                    avg_sentiment=summary.avg_sentiment,
                    cache_key=f"spike:{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                )
                logger.info("Crisis summary generated and stored")
                
        except Exception as e:
            logger.error(f"Crisis summary generation error: {e}")


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
