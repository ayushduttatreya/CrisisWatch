# CrisisWatch - Real-Time News Intelligence Dashboard

A production-grade sentiment monitoring system that tracks global news, analyzes sentiment trends, and detects crisis spikes in real-time.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│    Nginx    │────▶│   Backend   │
│  (React)    │     │  (Proxy)    │     │   (Flask)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                                                ▼
                                        ┌─────────────┐
                                        │   SQLite    │
                                        │    DB       │
                                        └─────────────┘
```

### Components

- **Frontend**: React + TypeScript + shadcn/ui + Vite
- **Backend**: Flask + Peewee ORM + APScheduler
- **Database**: SQLite (persistent storage)
- **Proxy**: Nginx (serves frontend + proxies API)

## Quick Start

### Local Development

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install Node.js dependencies (for frontend)
cd frontend
npm install

# 3. Start backend (terminal 1)
python app.py

# 4. Start frontend dev server (terminal 2)
cd frontend
npm run dev

# 5. Open browser
open http://localhost:5173
```

### Docker Production

```bash
# Build and start all services
docker-compose up --build

# Access application
open http://localhost
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/health` | Health check with DB status |
| `GET /api/articles` | Get latest articles (paginated) |
| `GET /api/stats` | System statistics + alerts |
| `GET /api/trend` | Sentiment trend data points |
| `GET /api/entities` | Entity leaderboard (24h) |
| `POST /api/ai/query` | Natural language query |

### Query Parameters

**GET /api/articles**
- `limit` (int, default: 20): Articles to return
- `order` (str, default: desc): asc or desc
- `ai` (bool, default: true): Include AI fields

**GET /api/entities**
- `hours` (int, default: 24): Time window
- `top` (int, default: 10): Number of entities

## Environment Variables

Create `.env` file:

```bash
# Required
NEWS_API_KEY=your_newsapi_key_here

# Optional (with defaults)
DATABASE_PATH=crisiswatch.db
FLASK_PORT=5000
FLASK_DEBUG=false
REFRESH_INTERVAL=600
SPIKE_THRESHOLD=-0.3
TREND_WINDOW_SIZE=60

# AI Features (disabled by default)
AI_ENABLED=false
OPENROUTER_API_KEY=optional_openrouter_key
```

## Deployment

### Render.com

1. Create new Web Service
2. Connect GitHub repo
3. Set environment variables in dashboard
4. Use Docker deployment

```yaml
# render.yaml (included)
services:
  - type: web
    name: crisiswatch
    runtime: docker
    envVars:
      - key: NEWS_API_KEY
        sync: false
```

## Logging

All system activity is logged with consistent format:

```
[2024-01-15 10:30:00] [INFO] [api] API: /api/stats - total=150, mood=-0.25, spike=False
[2024-01-15 10:30:00] [INFO] [pipeline] Pipeline complete: 10/12 articles stored
[2024-01-15 10:30:05] [WARNING] [trend] Crisis spike detected: {'type': 'crisis', 'msg': 'Negative sentiment spike detected'}
```

## Data Model

### Article
```
id: int
title: str
source: str
url: str
sentiment: float
category: str
entities: json (people, countries, organizations)
bias: str (left, right, neutral, unknown)
bias_confidence: float
fetched_at: datetime
```

### Trend Cache
- Rolling window (default: 60 points)
- Stores batch average sentiment
- Spike detection at threshold (-0.3)

## Development

### Project Structure

```
crisiswatch/
├── app.py                 # Flask API
├── scheduler.py           # Background jobs
├── config.py             # Settings
├── requirements.txt      # Python deps
├── docker-compose.yml    # Docker orchestration
├── database/
│   ├── models.py        # Peewee models
│   └── cache.py         # In-memory caches
├── analyzer/
│   ├── sentiment.py     # VADER analysis
│   ├── trend.py         # Spike detection
│   └── ...              # AI modules (disabled)
├── fetcher/
│   ├── newsapi.py       # NewsAPI source
│   └── rss.py           # RSS feeds
├── utils/
│   └── logger.py        # Centralized logging
└── frontend/
    ├── src/
    ├── package.json
    └── Dockerfile       # Multi-stage build
```

### Testing

```bash
# Run Python tests
pytest tests/

# Build frontend
cd frontend
npm run build
```

## Monitoring

- Health check: `GET /api/health`
- Logs: `docker-compose logs -f`
- DB: Inspect `data/crisiswatch.db`

## Troubleshooting

**Empty dashboard**
- Check `NEWS_API_KEY` is set
- Wait for first fetch cycle (10 min default)
- Check logs: `docker-compose logs backend`

**No trend data**
- Need minimum 10 data points for spike detection
- Wait for 2-3 fetch cycles
- Check `TREND_WINDOW_SIZE` setting

**AI features disabled**
- AI is disabled by default for stability
- Set `AI_ENABLED=true` after system is operational

## License

MIT

## Credits

Built with:
- [NewsAPI](https://newsapi.org) for news data
- [VADER](https://github.com/cjhutto/vaderSentiment) for sentiment analysis
- [shadcn/ui](https://ui.shadcn.com) for React components
- [Flask](https://flask.palletsprojects.com) for API
