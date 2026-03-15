# Fin Data Admin — AI Agent Context

## Project Overview

**Fin Data Admin** is a centralized financial data hub for managing automated
ingestion, normalization, analysis, and serving of market data across **stocks**
and **crypto**. The system mirrors the architecture of `sports-data-admin` but
replaces sports concepts with financial equivalents:

| Sports Concept       | Financial Equivalent                        |
| -------------------- | ------------------------------------------- |
| Leagues (NBA, NHL)   | Asset classes (STOCKS, CRYPTO)              |
| Teams                | Assets / Tickers (AAPL, BTC, ETH)          |
| Games                | Trading sessions / Market windows           |
| Play-by-play         | Tick data / OHLCV candles                   |
| Boxscores            | Session summaries (open, high, low, close)  |
| Odds (books)         | Exchange prices (Binance, Coinbase, NYSE)   |
| FairBet / +EV        | Cross-exchange arbitrage / Alpha signals    |
| Game flow narratives | Market narratives / Session analysis        |
| Social (team tweets) | Social sentiment (Twitter, Reddit, Discord) |

## Architecture

```
fin-data-admin/
├── api/          # FastAPI backend (Python 3.11+, async SQLAlchemy, PostgreSQL)
├── scraper/      # Celery-based data ingestion (prices, orderbook, social, on-chain)
├── web/          # Next.js admin dashboard (React, TypeScript)
├── infra/        # Docker Compose, Dockerfiles, deploy scripts
├── sql/          # Schema migrations
├── docs/         # Comprehensive documentation
├── data/         # Local artifacts (golden test data, analysis, backups)
└── packages/     # Shared JS libraries (future)
```

## Core Principles

1. **Stability over speed** — Never break existing pipelines for a new feature
2. **Predictable schemas** — Every column typed, every constraint explicit
3. **Zero silent failures** — Log every error with context; never swallow exceptions
4. **Traceable changes** — Alembic migrations, structured logging, audit trails
5. **Config as code** — Pydantic Settings, not scattered env vars

## Tech Stack

| Component        | Technology                |
| ---------------- | ------------------------- |
| API              | FastAPI 0.109+            |
| Database         | PostgreSQL 15+            |
| ORM              | SQLAlchemy 2.0+ (async)   |
| Migrations       | Alembic 1.13+             |
| Task Queue       | Celery 5.4+ / Redis       |
| Web UI           | Next.js 16+ / React 19+   |
| HTTP Client      | httpx 0.27+               |
| Config           | Pydantic Settings 2.5+    |
| Logging          | structlog 24.1+           |
| AI/ML            | OpenAI API (gpt-4o)       |
| Containerization | Docker Compose            |

## Data Sources

### Stocks
- **Yahoo Finance API** (yfinance) — OHLCV, fundamentals, dividends
- **Alpha Vantage** — Intraday, technicals, earnings
- **Polygon.io** — Real-time ticks, aggregates, news
- **SEC EDGAR** — Filings (10-K, 10-Q, 8-K)

### Crypto
- **Binance API** — Spot prices, order book, trades
- **CoinGecko** — Market data, volume, market cap
- **CoinMarketCap** — Rankings, metadata
- **On-chain** — Etherscan, blockchain.com (whale wallets, gas, txn volume)

### Cross-cutting
- **Social** — Twitter/X (cashtags, influencer accounts), Reddit (r/wallstreetbets, r/cryptocurrency)
- **News** — NewsAPI, Polygon news feed
- **Fear & Greed Index** — Alternative.me (crypto), CNN (stocks)

## Coding Standards

### Python (API & Scraper)
- Type hints on **all** functions
- Pydantic v2 models for request/response validation
- Structured logging via `structlog`
- Never use bare `except:` — always catch specific exceptions
- Async SQLAlchemy in API; sync in scraper

### TypeScript (Web)
- No `any` types — strict type checking
- Functional components with hooks
- CSS Modules for styling

### General
- 80%+ test coverage (pytest)
- Semantic git commits
- PR-based workflow

## Scheduled Jobs (UTC)

| Task                       | Cadence      | UTC Time | Purpose                              |
| -------------------------- | ------------ | -------- | ------------------------------------ |
| `ingest_daily_prices`      | Daily        | 05:00    | EOD OHLCV for stocks + crypto        |
| `ingest_intraday_prices`   | Every 5 min  | */5      | Live candles during market hours      |
| `sync_exchange_prices`     | Every 1 min  | */1      | Cross-exchange price sync (arb scan) |
| `collect_social_sentiment` | Every 30 min | */30     | Twitter/Reddit sentiment scrape       |
| `run_signal_pipeline`      | Every 15 min | */15     | Technical + fundamental signals       |
| `generate_market_analysis` | Daily        | 06:00    | AI narrative generation               |
| `run_daily_sweep`          | Daily        | 07:00    | Backfill, cleanup, reconciliation     |
| `sync_onchain_data`        | Every 15 min | */15     | Whale wallets, gas, DEX volume        |

## Key Concepts

### Alpha Signals (equiv. to +EV)
Cross-exchange price discrepancies, technical indicator convergence,
sentiment-price divergence, and on-chain whale accumulation patterns.
Each signal has a `confidence_tier` (HIGH, MEDIUM, LOW) and `signal_type`.

### Market Sessions (equiv. to Games)
Stock market sessions (9:30 AM – 4:00 PM ET) and 24/7 crypto windows.
Each session tracks OHLCV, volume profile, and key events.

### Asset Classes (equiv. to Leagues)
- `STOCKS` — US equities (NYSE, NASDAQ)
- `CRYPTO` — Top cryptocurrencies by market cap

### Exchanges (equiv. to Sportsbooks)
- Stocks: NYSE, NASDAQ, CBOE
- Crypto: Binance, Coinbase, Kraken, Bybit, OKX
