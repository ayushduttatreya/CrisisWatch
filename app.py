"""Flask API application for CrisisWatch."""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS
from peewee import fn

from config import get_settings
from database.models import Article, AISummary, init_database, close_database
from database.cache import alert_store, trend_cache, get_cache_stats
from scheduler import start_scheduler, stop_scheduler
from analyzer.entity_extractor import aggregate_entities
from analyzer.nl_query import query_news
from analyzer.ai_summary import get_summary_for_spike

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
            include_ai = request.args.get("ai", "true").lower() == "true"
            
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
                "articles": [a.to_dict(include_ai=include_ai) for a in articles]
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
            "ai_enabled": settings.AI_ENABLED,
        })
    
    # ============ AI Endpoints ============
    
    @app.route("/api/ai/summary", methods=["GET"])
    def get_ai_summary():
        """Get AI-generated crisis summary (only meaningful during spikes)."""
        try:
            # Try to get cached summary from database
            latest = AISummary.get_latest_crisis_summary()
            
            # If spike is active but no recent summary, generate one
            if trend_cache.is_spike() and settings.AI_CRISIS_SUMMARY:
                # Check if we need a fresh summary
                if not latest or (datetime.utcnow() - datetime.fromisoformat(latest.generated_at)).seconds > 300:
                    # Get recent negative articles for summary
                    negative_articles = (
                        Article.select()
                        .where(Article.sentiment < settings.SPIKE_THRESHOLD)
                        .order_by(Article.fetched_at.desc())
                        .limit(10)
                    )
                    
                    if negative_articles:
                        articles_list = [a.to_dict(include_ai=False) for a in negative_articles]
                        
                        # Run async summary generation
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            summary = loop.run_until_complete(get_summary_for_spike(articles_list))
                            loop.close()
                            
                            if summary:
                                # Store new summary
                                AISummary.create(
                                    summary_type="crisis",
                                    content=summary.summary,
                                    headline_count=summary.headline_count,
                                    avg_sentiment=summary.avg_sentiment,
                                )
                                return jsonify({
                                    "summary": summary.summary,
                                    "generated_at": summary.generated_at,
                                    "headline_count": summary.headline_count,
                                    "cached": False,
                                })
                        except Exception as e:
                            logger.error(f"Failed to generate summary: {e}")
            
            # Return cached summary if available
            if latest:
                return jsonify({
                    "summary": latest.content,
                    "generated_at": latest.generated_at,
                    "headline_count": latest.headline_count,
                    "cached": True,
                })
            
            # No summary available
            return jsonify({
                "summary": None,
                "message": "No crisis summary available. Summaries are generated during sentiment spikes.",
            })
            
        except Exception as e:
            logger.error(f"Error fetching AI summary: {e}")
            return jsonify({
                "summary": None,
                "error": "Failed to fetch summary"
            }), 500
    
    @app.route("/api/entities", methods=["GET"])
    def get_entities():
        """Get aggregated entity leaderboard from recent articles."""
        try:
            hours = request.args.get("hours", 24, type=int)
            top_n = request.args.get("top", 10, type=int)
            
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            # Fetch articles with entities in time window
            recent_articles = (
                Article.select()
                .where(
                    (Article.fetched_at > cutoff) & 
                    (Article.entities.is_null(False))
                )
                .order_by(Article.fetched_at.desc())
                .limit(100)
            )
            
            # Parse entities
            from analyzer.entity_extractor import ExtractedEntities
            entities_list = []
            for article in recent_articles:
                entities_dict = article.get_entities()
                if entities_dict:
                    entities_list.append(ExtractedEntities(
                        people=entities_dict.get("people", []),
                        countries=entities_dict.get("countries", []),
                        organizations=entities_dict.get("organizations", []),
                    ))
            
            # Aggregate and rank
            aggregated = aggregate_entities(entities_list, top_n=top_n)
            
            return jsonify({
                "top_entities": aggregated,
                "time_window_hours": hours,
                "articles_analyzed": len(entities_list),
            })
            
        except Exception as e:
            logger.error(f"Error fetching entities: {e}")
            return jsonify({
                "top_entities": {"people": [], "countries": [], "organizations": []},
                "error": "Failed to fetch entities"
            }), 500
    
    @app.route("/api/ai/query", methods=["POST"])
    def nl_query():
        """Natural language query over stored news data."""
        try:
            data = request.get_json()
            if not data or "q" not in data:
                return jsonify({
                    "error": "Missing required field: 'q'"
                }), 400
            
            query_text = data["q"].strip()
            if not query_text:
                return jsonify({
                    "error": "Query cannot be empty"
                }), 400
            
            max_context = data.get("max_context", 20)
            
            # Run async query
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(query_news(query_text, max_context=max_context))
                loop.close()
                
                return jsonify({
                    "answer": result.answer,
                    "sources_used": result.sources_used,
                    "generated_at": result.generated_at,
                    "success": result.success,
                })
            except Exception as e:
                logger.error(f"NL query processing failed: {e}")
                return jsonify({
                    "answer": "I'm unable to process your query at the moment. Please try again later.",
                    "success": False,
                }), 500
                
        except Exception as e:
            logger.error(f"Error processing NL query: {e}")
            return jsonify({
                "error": "Failed to process query"
            }), 500
    
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
