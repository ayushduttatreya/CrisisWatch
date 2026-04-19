"""Database models using Peewee ORM."""

import hashlib
from datetime import datetime
from typing import Optional

from peewee import (
    CharField,
    DateTimeField,
    FloatField,
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
    """News article with sentiment analysis."""
    
    title = TextField()
    source = CharField()
    url = TextField()
    sentiment = FloatField()
    category = CharField(default="general")
    hash = CharField(unique=True, index=True)
    fetched_at = DateTimeField(default=datetime.utcnow)
    
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
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "title": self.title,
            "source": self.source,
            "sentiment": self.sentiment,
            "category": self.category,
            "url": self.url,
            "fetched_at": self.fetched_at.isoformat(),
        }


def init_database() -> None:
    """Initialize database tables."""
    db.connect(reuse_if_open=True)
    db.create_tables([Article], safe=True)


def close_database() -> None:
    """Close database connection."""
    if not db.is_closed():
        db.close()
