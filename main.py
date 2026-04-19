"""Entry point for CrisisWatch application."""

import logging
import sys

from app import create_app
from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    settings = get_settings()
    
    logger.info("=" * 50)
    logger.info("CrisisWatch - Starting application")
    logger.info("=" * 50)
    logger.info(f"Database: {settings.DATABASE_PATH}")
    logger.info(f"Refresh interval: {settings.REFRESH_INTERVAL}s")
    logger.info(f"NewsAPI configured: {bool(settings.NEWS_API_KEY)}")
    logger.info(f"RSS feeds: {len(settings.RSS_FEEDS)}")
    logger.info("=" * 50)
    
    app = create_app()
    
    try:
        app.run(
            host="0.0.0.0",
            port=settings.get_port(),
            debug=settings.FLASK_DEBUG,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    finally:
        from scheduler import stop_scheduler
        from app import scheduler
        if scheduler:
            stop_scheduler(scheduler)


if __name__ == "__main__":
    main()
