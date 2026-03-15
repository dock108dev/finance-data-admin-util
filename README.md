# Fin Data Admin

Centralized financial data hub for automated ingestion, normalization, analysis,
and serving of market data across **stocks** and **crypto**. Built as the
financial equivalent of [sports-data-admin](../sports-data-admin).

## Quick Start

```bash
# 1. Clone and navigate
cd fin-data-admin

# 2. Copy environment config
cp .env.example .env
# Edit .env with your API keys

# 3. Start all services
cd infra
docker compose --profile dev up -d --build

# 4. Apply database migrations
docker compose exec api alembic upgrade head

# 5. Access the admin UI
open http://localhost:3000/admin
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Web Admin   │────▶│   FastAPI     │────▶│ PostgreSQL  │
│  (Next.js)   │     │   Backend     │     │   15+       │
└─────────────┘     └──────┬───────┘     └──────▲──────┘
                           │                     │
                    ┌──────▼───────┐             │
                    │    Redis      │             │
                    │  (Broker)     │             │
                    └──────┬───────┘             │
                           │                     │
                    ┌──────▼───────┐             │
                    │   Celery      │─────────────┘
                    │  (Scraper)    │
                    └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        Yahoo Finance  Binance    Twitter/Reddit
        Alpha Vantage  CoinGecko  NewsAPI
        Polygon.io     Etherscan  Fear & Greed
```

## Key Features

- **Multi-source price ingestion** — OHLCV from Yahoo Finance, Binance, Polygon.io
- **Cross-exchange arbitrage detection** — Real-time price discrepancy scanning
- **Technical indicator pipeline** — RSI, MACD, Bollinger, VWAP, and more
- **Social sentiment analysis** — Twitter cashtags, Reddit mentions, Fear & Greed
- **On-chain analytics** — Whale wallet tracking, gas prices, DEX volume
- **AI market narratives** — GPT-4o session analysis and signal explanation
- **Admin dashboard** — Asset browser, signal viewer, control panel, portfolio tracker

## Documentation

See [docs/INDEX.md](docs/INDEX.md) for the full documentation index.

## Project Structure

```
fin-data-admin/
├── api/            # FastAPI backend
├── scraper/        # Celery data ingestion
├── web/            # Next.js admin UI
├── infra/          # Docker & deployment
├── sql/            # Database migrations
├── docs/           # Documentation
├── data/           # Local artifacts
└── packages/       # Shared libraries
```
