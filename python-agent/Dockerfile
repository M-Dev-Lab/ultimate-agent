FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 agent && \
    mkdir -p /app/data /app/logs && \
    chown -R agent:agent /app

# Set working directory
WORKDIR /app

# ==================== Dependencies Stage ====================
FROM base as dependencies

USER root
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ==================== Security Scanning Stage ====================
FROM dependencies as security

# Install security scanning tools
RUN pip install --no-cache-dir safety bandit

# Run security checks
RUN safety check || true && \
    bandit -r app -f json -o /tmp/bandit-report.json || true

# ==================== Runtime Stage ====================
FROM dependencies as runtime

USER agent

# Copy application code
COPY --chown=agent:agent . .

# Create necessary directories
RUN mkdir -p data logs && \
    chmod 755 data logs

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose ports
EXPOSE 8000 8001

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
