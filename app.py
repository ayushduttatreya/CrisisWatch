"""Flask API application for CrisisWatch."""

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
from utils.logger import get_logger

# Use centralized logger
logger = get_logger("api")

# Wrap settings load to prevent hard crash if config.py somehow fails
try:
    settings = get_settings()
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    # Fallback to minimal settings if everything fails
    from config import Settings
    settings = Settings()

scheduler = None


def create_app() -> Flask:
    """Application factory for Flask - API-only service."""
    app = Flask(__name__)
    CORS(app, origins="*")
    
    # Initialize database
    init_database()
    
    # Start background scheduler (only once)
    global scheduler
    if scheduler is None:
        try:
            scheduler = start_scheduler()
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
    
    @app.teardown_appcontext
    def close_db(error):
        """Close database connection after each request."""
        close_database()
        
    logger.info("Backend initialized successfully")
    
    # ============ API Routes ============
    
    @app.route("/api/articles", methods=["GET"])
    def get_articles():
        """Get articles with pagination and ordering."""
        try:
            limit = request.args.get("limit", 20, type=int)
            order = request.args.get("order", "desc").lower()
            include_ai = request.args.get("ai", "true").lower() == "true"
            
            hours = request.args.get("hours", 24, type=int)
            # Hard limit maximum query window to 48 hours to strictly prevent older data
            cutoff_hours = min(hours, 48)
            cutoff = datetime.utcnow() - timedelta(hours=cutoff_hours)
            
            # Validate params
            limit = max(1, min(limit, 100))
            sort_mode = request.args.get("sort", "impact").lower()
            
            # Build query with strict baseline time constraint
            # Fallback to fetched_at if published_at is null
            query = Article.select().where(
                (Article.published_at >= cutoff) | 
                (Article.published_at.is_null() & (Article.fetched_at >= cutoff))
            )
            
            articles_db = list(query)
            
            # Compute time-aware scores in Python
            now = datetime.utcnow()
            scored_articles = []
            
            for a in articles_db:
                score_data = a.get_time_weighted_score(now)
                scored_articles.append((a, score_data))
                
                # Log score calculation for debugging
                logger.debug(
                    f"Article '{a.title[:30]}...' -> Age: {score_data['age_hours']}h | "
                    f"Weight: {score_data['freshness_weight']} | Score: {score_data['score']}"
                )
            
            # Python in-memory sorting
            if sort_mode == "latest":
                # Sort strictly by publication time
                scored_articles.sort(
                    key=lambda x: x[0].published_at or x[0].fetched_at, 
                    reverse=(order == "desc")
                )
            else:
                # Default "impact": sort by score ascending (most negative sentiment first)
                # If order == asc, most severe crises are at the top
                scored_articles.sort(
                    key=lambda x: x[1]['score'], 
                    reverse=(order == "desc")
                )
            
            # Apply limit after ranking
            final_articles = [
                a.to_dict(include_ai=include_ai, computed_score=score_data) 
                for a, score_data in scored_articles[:limit]
            ]
            
            logger.info(f"API: /api/articles - returned {len(final_articles)} articles (sort={sort_mode})")
            
            return jsonify({
                "articles": final_articles,
                "count": len(final_articles)
            })
            
        except Exception as e:
            logger.error(f"API ERROR: /api/articles - {e}", exc_info=True)
            return jsonify({
                "articles": [],
                "count": 0,
                "error": "Failed to fetch articles"
            }), 500
    
    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        """Get system statistics and alerts."""
        try:
            # Get total article count (handle empty DB)
            total = Article.select().count() or 0
            
            # Get mood average from cache (handle empty cache)
            cache_stats = get_cache_stats()
            mood_avg = cache_stats.get("average_sentiment", 0.0) or 0.0
            is_spike = cache_stats.get("is_spike", False) or False
            
            # Get recent alerts
            alerts = alert_store.get_alerts(10) or []
            
            logger.info(f"API: /api/stats - total={total}, mood={mood_avg:.3f}, spike={is_spike}")
            
            return jsonify({
                "total": total,
                "mood_avg": round(mood_avg, 3),
                "is_spike": is_spike,
                "alerts": alerts,
            })
            
        except Exception as e:
            logger.error(f"API ERROR: /api/stats - {e}", exc_info=True)
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
            
            # Ensure we always return a valid array
            if not isinstance(trend, list):
                trend = []
            
            logger.info(f"API: /api/trend - returned {len(trend)} data points")
            
            return jsonify({
                "trend": trend,
                "count": len(trend)
            })
            
        except Exception as e:
            logger.error(f"API ERROR: /api/trend - {e}", exc_info=True)
            return jsonify({
                "trend": [],
                "count": 0,
                "error": "Failed to fetch trend"
            }), 500
    
    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        try:
            # Test database connection
            Article.select().limit(1).count()
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        response = {
            "status": "healthy",
            "database": db_status,
            "scheduler_running": scheduler.running if scheduler else False,
            "ai_enabled": settings.AI_ENABLED,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        logger.info(f"API: /api/health - {response['status']}")
        return jsonify(response)
    
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
                    ((Article.published_at > cutoff) | (Article.published_at.is_null() & (Article.fetched_at > cutoff))) & 
                    (Article.entities.is_null(False))
                )
                .order_by(Article.published_at.desc(), Article.fetched_at.desc())
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
