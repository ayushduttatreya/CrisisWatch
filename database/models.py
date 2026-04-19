"""Database models using Peewee ORM."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

from peewee import (
    CharField,
    DateTimeField,
    FloatField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

from config import get_settings

settings = get_settings()
db = SqliteDatabase(settings.DATABASE_PATH)


class BaseModel(Model):
    """Base model with database connection."""
    
    class Meta:
        database = db


class Article(BaseModel):
    """News article with sentiment analysis and AI enrichment."""
    
    title = TextField()
    source = CharField()
    url = TextField()
    sentiment = FloatField()
    category = CharField(default="general")
    hash = CharField(unique=True, index=True)
    fetched_at = DateTimeField(default=datetime.utcnow)
    published_at = DateTimeField(null=True)
    
    # AI-enriched fields
    entities = TextField(null=True)  # JSON string: {"people": [], "countries": [], "organizations": []}
    bias = CharField(null=True)  # "left", "right", "neutral", "unknown"
    bias_confidence = FloatField(null=True)
    
    def set_entities(self, entities_dict: Dict[str, Any]) -> None:
        """Store entities as JSON string."""
        self.entities = json.dumps(entities_dict) if entities_dict else None
    
    def get_entities(self) -> Optional[Dict[str, Any]]:
        """Retrieve entities as dictionary."""
        if self.entities:
            try:
                return json.loads(self.entities)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_bias(self, bias: str, confidence: float) -> None:
        """Set bias classification."""
        self.bias = bias
        self.bias_confidence = confidence
    
    @classmethod
    def generate_hash(cls, title: str, url: str) -> str:
        """Generate SHA-256 hash of title + url for deduplication."""
        content = f"{title}{url}".encode("utf-8")
        return hashlib.sha256(content).hexdigest()
    
    @classmethod
    def create_from_data(
        cls,
        title: str,
        source: str,
        url: str,
        sentiment: float,
        category: str = "general",
        published_at: Optional[str] = None,
    ) -> Optional["Article"]:
        """Create article with deduplication check."""
        article_hash = cls.generate_hash(title, url)
        
        # Check for existing article
        if cls.select().where(cls.hash == article_hash).exists():
            return None
        
        return cls.create(
            title=title,
            source=source,
            url=url,
            sentiment=sentiment,
            category=category,
            hash=article_hash,
            published_at=published_at,
        )
    
    def get_time_weighted_score(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate time-decayed sentiment score.
        score = sentiment * max(0, 1 - (age_hours / 24))
        """
        now = now or datetime.utcnow()
        pub_time = self.published_at or self.fetched_at
        
        # Calculate age in hours
        age_hours = max(0.0, (now - pub_time).total_seconds() / 3600.0)
        
        # Calculate freshness weight (0 to 1)
        freshness_weight = max(0.0, 1.0 - (age_hours / 24.0))
        
        # Calculate final score
        score = self.sentiment * freshness_weight
        
        return {
            "age_hours": round(age_hours, 2),
            "freshness_weight": round(freshness_weight, 4),
            "score": round(score, 4),
        }
    
    def to_dict(self, include_ai: bool = True, computed_score: Optional[Dict[str, Any]] = None) -> dict:
        """Convert to dictionary for API responses."""
        result = {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "sentiment": self.sentiment,
            "category": self.category,
            "url": self.url,
            "fetched_at": self.fetched_at.isoformat(),
            "published_at": self.published_at.isoformat() if hasattr(self.published_at, 'isoformat') else self.published_at,
        }
        
        if computed_score:
            result.update(computed_score)
        
        if include_ai:
            result["entities"] = self.get_entities()
            result["bias"] = self.bias
            result["bias_confidence"] = self.bias_confidence
        
        return result


class AISummary(BaseModel):
    """Cached AI-generated crisis summaries."""
    
    summary_type = CharField(default="crisis")  # Type of summary
    content = TextField()  # The generated summary text
    headline_count = IntegerField(default=0)
    avg_sentiment = FloatField()
    generated_at = DateTimeField(default=datetime.utcnow)
    cache_key = CharField(index=True, null=True)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "summary": self.content,
            "summary_type": self.summary_type,
            "headline_count": self.headline_count,
            "avg_sentiment": self.avg_sentiment,
            "generated_at": self.generated_at.isoformat(),
        }
    
    @classmethod
    def get_latest_crisis_summary(cls) -> Optional["AISummary"]:
        """Get the most recent crisis summary."""
        try:
            return (
                cls.select()
                .where(cls.summary_type == "crisis")
                .order_by(cls.generated_at.desc())
                .first()
            )
        except Exception:
            return None


def init_database() -> None:
    """Initialize database tables and handle schema migrations."""
    db.connect(reuse_if_open=True)
    db.create_tables([Article, AISummary], safe=True)
    
    # Run simple migrations for missing columns
    from peewee import OperationalError
    
    try:
        db.execute_sql('ALTER TABLE article ADD COLUMN entities TEXT;')
    except OperationalError:
        pass
        
    try:
        db.execute_sql('ALTER TABLE article ADD COLUMN bias VARCHAR(255);')
    except OperationalError:
        pass
        
    try:
        db.execute_sql('ALTER TABLE article ADD COLUMN bias_confidence REAL;')
    except OperationalError:
        pass
        
    try:
        db.execute_sql('ALTER TABLE article ADD COLUMN published_at DATETIME;')
    except OperationalError:
        pass
        
    # Clean stale data on boot
    clean_stale_data()

def clean_stale_data() -> None:
    """Delete articles older than 24 hours to ensure strict time-based correctness."""
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        # Delete where published_at is explicitly old, OR (if null) where fetched_at is old
        # Fallback to fetched_at ensures legacy polluted data is wiped out too
        q = Article.delete().where(
            (Article.published_at < cutoff) | 
            (Article.published_at.is_null() & (Article.fetched_at < cutoff))
        )
        deleted = q.execute()
        if deleted > 0:
            logger.info(f"Database Cleanup: Deleted {deleted} stale articles older than 24 hours.")
    except Exception as e:
        logger.error(f"Failed to clean stale data: {e}")


def close_database() -> None:
    """Close database connection."""
    if not db.is_closed():
        db.close()
