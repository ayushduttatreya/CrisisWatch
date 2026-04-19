FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create volume mount point for database persistence
VOLUME ["/app/data"]

# Environment variables with defaults
ENV DATABASE_PATH=/app/data/crisiswatch.db
ENV PORT=5000
ENV FLASK_DEBUG=false
ENV REFRESH_INTERVAL=600

# Expose port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT}/api/health')" || exit 1

# Run with gunicorn
CMD exec gunicorn 'app:create_app()' --bind 0.0.0.0:${PORT} --workers 2 --timeout 120 --access-logfile -
