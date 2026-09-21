# Dockerfile for Micro Trading Bot - Clean Architecture Implementation

# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY core/ ./core/
COPY data/ ./data/
COPY scripts/ ./scripts/
COPY webapp/ ./webapp/
COPY config.py dashboard.py runtime_control.py setup.py README.md ./

# Install package metadata without adding a second dependency resolution step.
RUN pip install --no-cache-dir --no-deps .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash tradingbot && \
    mkdir -p /app/runtime && chown -R tradingbot:tradingbot /app

# Switch to non-root user
USER tradingbot

# Expose the monitoring web application
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Default command (can be overridden)
CMD ["gunicorn", "--workers=1", "--threads=4", "--bind=0.0.0.0:8080", "--access-logfile=-", "webapp.server:app"]
