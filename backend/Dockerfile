# Stage 1: development (Django runserver with hot reload)
FROM python:3.12-slim-bookworm AS development

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ libpq-dev libffi-dev libssl-dev \
    libgdal-dev gdal-bin postgresql-client curl git \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=config.settings.development

WORKDIR /app

COPY requirements/ requirements/
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements/base.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Stage 2: Builder
FROM python:3.12-slim-bookworm AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libgdal-dev \
    gdal-bin \
    postgresql-client \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Copy requirements
COPY requirements/ requirements/

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install -r requirements/base.txt

# Stage 2: Production
FROM python:3.12-slim-bookworm AS production

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgdal32 \
    gdal-bin \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r inhealth && useradd -r -g inhealth inhealth

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PORT=8000 \
    ASGI_PORT=8001

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=inhealth:inhealth . .

# Create required directories
RUN mkdir -p /app/staticfiles /app/media /app/logs && \
    chown -R inhealth:inhealth /app

# Switch to non-root user
USER inhealth

# Collect static files
RUN python manage.py collectstatic --noinput --settings=config.settings.production || true

# Expose ports
EXPOSE 8000 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/v1/health/ || exit 1

# Default command: run Daphne for ASGI (supports both HTTP and WebSocket)
CMD ["sh", "-c", "daphne -b 0.0.0.0 -p ${ASGI_PORT} config.asgi:application & gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers 4 --threads 2 --worker-class gthread --timeout 120 --keep-alive 5 --max-requests 1000 --max-requests-jitter 100 --access-logfile - --error-logfile - && wait"]
