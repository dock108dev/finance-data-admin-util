# Local Development Guide

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

## Quick Start (Docker)

```bash
# Start infrastructure
cd infra
docker compose up -d postgres redis

# Apply schema
docker compose exec postgres psql -U postgres -d findata -f /docker-entrypoint-initdb.d/000_core_schema.sql

# Start all services
docker compose --profile dev up -d --build

# Access:
#   API:  http://localhost:8000
#   Web:  http://localhost:3000
#   DB:   postgresql://postgres:postgres@localhost:5432/findata
```

## Manual Setup

### API

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Copy .env
cp ../.env.example .env

# Run
uvicorn main:app --reload --port 8000
```

### Scraper

```bash
cd scraper
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,social]"

# Worker
celery -A fin_scraper.celery_app worker -l info -Q fin-scraper

# Beat (separate terminal)
celery -A fin_scraper.celery_app beat -l info
```

### Web

```bash
cd web
npm install
npm run dev
```

## Database

```bash
# Connect
psql postgresql://postgres:postgres@localhost:5432/findata

# Apply schema
psql postgresql://postgres:postgres@localhost:5432/findata -f sql/000_core_schema.sql

# Reset
dropdb findata && createdb findata
psql findata -f sql/000_core_schema.sql
```

## Testing

```bash
# API tests
cd api && pytest --cov

# Scraper tests
cd scraper && pytest --cov
```

## Environment Variables

See `.env.example` for all required variables. Key ones:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `API_KEY` | Yes | API authentication key |
| `ALPHA_VANTAGE_API_KEY` | For stocks | Alpha Vantage key |
| `POLYGON_API_KEY` | For stocks | Polygon.io key |
| `BINANCE_API_KEY` | For crypto | Binance API key |
| `COINGECKO_API_KEY` | For crypto | CoinGecko key |
| `OPENAI_API_KEY` | For analysis | OpenAI key |
