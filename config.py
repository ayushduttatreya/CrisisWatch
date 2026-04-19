"""Configuration management for CrisisWatch."""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(extra='ignore')
    
    # NewsAPI
    NEWS_API_KEY: str = ""
    NEWS_API_URL: str = "https://newsapi.org/v2/top-headlines"
    
    # Categories to fetch from NewsAPI
    NEWS_CATEGORIES: List[str] = ["business", "world"]
    
    # RSS Feeds - Curated high-quality sources (20 total)
    # Focus: Geopolitics, markets, macro, conflict, policy - NO noise
    RSS_FEEDS: List[str] = [
        # === Tier 1: Premium Global ===
        "https://feeds.bloomberg.com/news.rss",              # Markets & macro
        "https://feeds.reuters.com/reuters/businessNews",   # Global business
        "https://feeds.reuters.com/reuters/worldNews",       # Global affairs
        "https://feeds.ft.com/ft/news/global-economy",      # FT global economy
        "https://feeds.a.dj.com/rss/RSSWorldNews.xml",      # WSJ world
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",     # WSJ markets
        
        # === Tier 2: Quality International ===
        "http://feeds.bbci.co.uk/news/world/rss.xml",       # BBC world
        "http://feeds.bbci.co.uk/news/business/rss.xml",    # BBC business
        "https://feeds.theguardian.com/theguardian/world/rss",  # Guardian world
        "https://feeds.theguardian.com/theguardian/business/rss", # Guardian business
        "https://www.aljazeera.com/xml/rss/all.xml",        # Geopolitics / conflict zones
        
        # === Tier 3: India Premium ===
        "https://www.business-standard.com/rss/home_page_top_stories.rss",  # BS top
        "https://www.business-standard.com/rss/markets.rss",                 # BS markets
        "https://www.moneycontrol.com/rss/news.xml",                         # MoneyControl
        "https://www.moneycontrol.com/rss/business.xml",                     # MC business
        "https://www.thehindu.com/business/?service=rss",                     # Hindu business
        "https://www.thehindu.com/news/international/?service=rss",         # Hindu world
        
        # === Tier 4: Policy & Geopolitics ===
        "https://feeds.apnews.com/APNews",                  # AP breaking
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  # NYT world
        "https://www.politico.com/rss/politicopicks.xml",    # US policy
    ]
    
    # Content filtering - articles must match these topics to be stored
    # Empty list = no filtering. Add keywords to filter for relevance.
    CONTENT_FILTERS: List[str] = []
    # Example: ["war", "conflict", "crisis", "market", "economy", "gdp", "inflation", "election", "policy", "trade", "sanctions", "fed", "rbi", "oil", "energy"]
    
    # Keywords that indicate low-value content (rejected if found in title)
    NOISE_KEYWORDS: List[str] = [
        "celebrity", "bollywood", "hollywood", "movie", "film", "actor", "actress",
        "sports", "cricket", "football", "ipl", "match", "score", "player",
        "entertainment", "gossip", "fashion", "beauty", "recipe", "cooking",
        "horoscope", "astrology", "zodiac", "dating", "wedding", "marriage",
        "viral", "meme", "tiktok", "instagram", "trending", "viral video",
    ]
    
    # Database
    DATABASE_PATH: str = "crisiswatch.db"
    
    # Scheduler
    REFRESH_INTERVAL: int = 600  # 10 minutes
    
    # Flask - PORT can override FLASK_PORT for Docker compatibility
    FLASK_PORT: int = 5000
    PORT: Optional[int] = None
    FLASK_DEBUG: bool = False
    
    @field_validator('PORT')
    @classmethod
    def port_priority(cls, v: Optional[int], info) -> Optional[int]:
        """Ensure PORT takes priority over FLASK_PORT when both are set."""
        if v is not None:
            return v
        return None
    
    def get_port(self) -> int:
        """Get effective port (PORT overrides FLASK_PORT)."""
        return self.PORT if self.PORT is not None else self.FLASK_PORT
    
    # Trend analysis
    TREND_WINDOW_SIZE: int = 60
    SPIKE_THRESHOLD: float = -0.3
    
    # OpenRouter AI Configuration
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "anthropic/claude-3.5-haiku"
    OPENROUTER_TIMEOUT: int = 30
    OPENROUTER_MAX_CONCURRENT: int = 5
    
    # AI Features Toggle
    AI_ENABLED: bool = True
    AI_ENTITY_EXTRACTION: bool = True
    AI_BIAS_DETECTION: bool = True
    AI_CRISIS_SUMMARY: bool = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
