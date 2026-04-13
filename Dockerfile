# Stage 1: Build frontend
FROM node:22-slim AS frontend
WORKDIR /app/apps/viewer-web
COPY apps/viewer-web/package.json apps/viewer-web/package-lock.json ./
RUN npm ci
COPY apps/viewer-web/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.11-slim AS runtime
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy workspace files
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY apps/viewer-api/ apps/viewer-api/

# Install Python deps
RUN uv sync --frozen --no-dev --package viewer-api

# Copy built frontend
COPY --from=frontend /app/apps/viewer-web/dist apps/viewer-web/dist

# Create data directory for SQLite
RUN mkdir -p /data

ENV DATABASE_URL=sqlite:////data/viewer.db
EXPOSE 8000

CMD ["uv", "run", "--package", "viewer-api", "uvicorn", "viewer_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
