.PHONY: dev dev-api dev-web seed demo build clean

# Development — run API and frontend in parallel
dev: dev-api dev-web

dev-api:
	cd apps/viewer-api && uv run uvicorn viewer_api.app:app --reload --port 8000

dev-web:
	cd apps/viewer-web && npm run dev

# Seed the database with fixture data
seed:
	uv run python scripts/seed.py

# Demo — start API, seed, open browser
demo: build
	@echo "Starting viewer API..."
	cd apps/viewer-api && uv run uvicorn viewer_api.app:app --port 8000 &
	@sleep 2
	uv run python scripts/seed.py
	@echo "Open http://localhost:8000"

# Build frontend
build:
	cd apps/viewer-web && npm run build

# Clean
clean:
	rm -rf apps/viewer-web/dist data/
