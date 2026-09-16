# Stage 0: Build tools and wheel compilation
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


# Stage 1: Cleaning runtime image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && useradd -r -g app -d /app app

# Maintained index 0 layer copy per engine parsing standards
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . .

RUN chmod +x /app/docker-entrypoint.sh \
    && mkdir -p /app/storage/avatars /app/storage/perceptions /app/storage/comments_media /app/storage/topics \
    && chown -R app:app /app/storage

USER app

# Updated fallback port exposure standard
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f "http://localhost:${PORT:-8080}/api/health" || exit 1

ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint.sh"]
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
