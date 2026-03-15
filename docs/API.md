# API Reference

Base URL: `http://localhost:8000`

All endpoints (except `/healthz`) require `X-API-Key` header.

## Health

```
GET /healthz
→ {"status": "ok"}
```

## Markets

```
GET /api/markets/assets
    ?asset_class=STOCKS|CRYPTO
    ?sector=Technology
    ?is_active=true
    ?limit=100&offset=0

GET /api/markets/assets/{id}

GET /api/markets/sessions
    ?asset_id=1
    ?asset_class=CRYPTO
    ?start_date=2024-01-01
    ?end_date=2024-01-31
    ?status=closed

GET /api/markets/sessions/{id}

GET /api/markets/candles/{asset_id}
    ?interval=5m|1h|1d
    ?start=2024-01-01T00:00:00Z
    ?end=2024-01-02T00:00:00Z
    ?limit=500
```

## Signals

```
GET /api/signals/alpha
    ?signal_type=CROSS_EXCHANGE_ARB|TECHNICAL_BREAKOUT|SENTIMENT_DIVERGENCE
    ?confidence_tier=HIGH|MEDIUM|LOW
    ?direction=LONG|SHORT
    ?min_strength=0.5
    ?outcome=HIT|MISS|EXPIRED|PENDING

GET /api/signals/arbitrage
    ?asset_id=1
    ?min_arb_pct=0.5

GET /api/signals/sentiment
    ?asset_id=1
    ?asset_class_id=2

GET /api/signals/analysis/{session_id}
```

## Admin

```
POST /api/admin/tasks/trigger
    Body: {"task_name": "ingest_daily_prices", "params": {...}}

GET /api/admin/tasks/registry

GET /api/admin/tasks/runs
    ?scraper_type=price_ingest
    ?status=completed|failed

GET /api/admin/pipeline/jobs
    ?phase=signal_pipeline_crypto

POST /api/admin/pipeline/{asset_id}/run
    ?session_date=2024-01-15

GET /api/admin/data/conflicts
    ?conflict_type=duplicate_candle
    ?unresolved_only=true

POST /api/admin/exchange/sync
    ?asset_class=CRYPTO
```
