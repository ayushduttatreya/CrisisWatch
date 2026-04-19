"""Flask API application for CrisisWatch."""

import logging
from typing import Dict, Any

from flask import Flask, jsonify, request
from flask_cors import CORS
from peewee import fn

from config import get_settings
from database.models import Article, init_database, close_database
from database.cache import alert_store, trend_cache, get_cache_stats
from scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()
scheduler = None


def create_app() -> Flask:
    """Application factory for Flask."""
    app = Flask(__name__, static_folder="static", static_url_path="")
    CORS(app)
    
    # Initialize database
    init_database()
    
    # Start background scheduler (only once)
    global scheduler
    if scheduler is None:
        scheduler = start_scheduler()
    
    @app.teardown_appcontext
    def close_db(error):
        """Close database connection after each request."""
        close_database()
    
    # ============ API Routes ============
    
    @app.route("/api/articles", methods=["GET"])
    def get_articles():
        """Get articles with pagination and ordering."""
        try:
            limit = request.args.get("limit", 10, type=int)
            order = request.args.get("order", "desc").lower()
            
            # Validate params
            limit = max(1, min(limit, 100))  # Clamp between 1-100
            
            # Build query
            query = Article.select()
            
            if order == "asc":
                query = query.order_by(Article.fetched_at.asc())
            else:
                query = query.order_by(Article.fetched_at.desc())
            
            articles = list(query.limit(limit))
            
            return jsonify({
                "articles": [a.to_dict() for a in articles]
            })
            
        except Exception as e:
            logger.error(f"Error fetching articles: {e}")
            return jsonify({
                "articles": [],
                "error": "Failed to fetch articles"
            }), 500
    
    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        """Get system statistics and alerts."""
        try:
            # Get total article count
            total = Article.select().count()
            
            # Get mood average from cache
            cache_stats = get_cache_stats()
            
            # Get recent alerts
            alerts = alert_store.get_alerts(10)
            
            return jsonify({
                "total": total,
                "mood_avg": round(cache_stats["average_sentiment"], 3),
                "is_spike": cache_stats["is_spike"],
                "alerts": alerts,
            })
            
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            return jsonify({
                "total": 0,
                "mood_avg": 0.0,
                "is_spike": False,
                "alerts": [],
                "error": "Failed to fetch stats"
            }), 500
    
    @app.route("/api/trend", methods=["GET"])
    def get_trend():
        """Get sentiment trend data."""
        try:
            trend = trend_cache.get_trend()
            
            return jsonify({
                "trend": trend
            })
            
        except Exception as e:
            logger.error(f"Error fetching trend: {e}")
            return jsonify({
                "trend": [],
                "error": "Failed to fetch trend"
            }), 500
    
    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "scheduler_running": scheduler.running if scheduler else False,
        })
    
    # Serve frontend
    @app.route("/", methods=["GET"])
    def index():
        """Serve the dashboard."""
        return app.send_static_file("index.html")
    
    return app


# For direct execution (development)
if __name__ == "__main__":
    app = create_app()
    
    try:
        app.run(
            host="0.0.0.0",
            port=settings.FLASK_PORT,
            debug=settings.FLASK_DEBUG,
            use_reloader=False,  # Prevent double scheduler start
        )
    finally:
        if scheduler:
            stop_scheduler(scheduler)
