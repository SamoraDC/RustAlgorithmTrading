# Multi-stage build for FastAPI Observability Server
ARG PYTHON_VERSION=3.11

# Stage 1: Builder - Install dependencies
FROM python:${PYTHON_VERSION}-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: React Dashboard Builder (if separate build needed)
FROM node:18-alpine as dashboard-builder

WORKDIR /dashboard

# Copy dashboard source
COPY dashboard/package*.json ./
RUN npm ci --only=production

COPY dashboard/ ./
RUN npm run build

# Stage 3: Runtime - Final lightweight image
FROM python:${PYTHON_VERSION}-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DUCKDB_PATH=/app/data/metrics.duckdb \
    SQLITE_PATH=/app/data/trading.db \
    LOG_PATH=/app/logs

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy React build from dashboard-builder (if separate)
COPY --from=dashboard-builder /dashboard/build /app/static

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/metrics /app/src

# Copy application code
COPY . /app/src/

# Create non-root user for security
RUN groupadd -r trading && \
    useradd -r -g trading -u 1000 trading && \
    chown -R trading:trading /app

# Switch to non-root user
USER trading

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI with Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "info"]
