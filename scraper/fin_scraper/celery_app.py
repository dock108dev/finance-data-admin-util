"""Celery application and Beat schedule — SSOT for all scheduled tasks.

Equivalent to sports-data-admin's celery_app.py.
All scheduled ingestion, sync, and pipeline tasks are defined here.
"""

import os
from celery import Celery
from celery.schedules import crontab


# ── Celery App ───────────────────────────────────────────────────────────────

app = Celery(
    "fin_scraper",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="fin-scraper",
    task_routes={
        "fin_scraper.jobs.*": {"queue": "fin-scraper"},
    },
)

# Explicitly include all task modules (autodiscover only finds tasks.py by default)
app.conf.include = [
    "fin_scraper.jobs.price_tasks",
    "fin_scraper.jobs.social_tasks",
    "fin_scraper.jobs.signal_tasks",
    "fin_scraper.jobs.onchain_tasks",
    "fin_scraper.jobs.analysis_tasks",
    "fin_scraper.jobs.sweep_tasks",
    "fin_scraper.jobs.macro_tasks",
]


# ── Beat Schedule ────────────────────────────────────────────────────────────
# All times in UTC. Equivalent to sports-data-admin's _scheduled_tasks.

_always_on_schedule = {
    # Cross-exchange price sync — every 1 minute (crypto arb detection)
    "exchange-price-sync-every-1-min": {
        "task": "fin_scraper.jobs.price_tasks.sync_exchange_prices",
        "schedule": 60.0,  # Every 60 seconds
        "kwargs": {"asset_class": "CRYPTO"},
    },
}

_scheduled_tasks = {
    # ── Daily Ingestion ──────────────────────────────────────────────────

    # EOD price ingestion — 5:00 AM UTC (midnight ET)
    "daily-price-ingestion-5am-utc": {
        "task": "fin_scraper.jobs.price_tasks.ingest_daily_prices",
        "schedule": crontab(hour=5, minute=0),
        "kwargs": {},
    },

    # Fundamental data — 6:00 AM UTC
    "daily-fundamentals-6am-utc": {
        "task": "fin_scraper.jobs.price_tasks.ingest_fundamentals",
        "schedule": crontab(hour=6, minute=0),
        "kwargs": {},
    },

    # Market analysis generation — 7:00 AM UTC (2:00 AM ET)
    "daily-analysis-generation-7am-utc": {
        "task": "fin_scraper.jobs.analysis_tasks.generate_daily_analyses",
        "schedule": crontab(hour=7, minute=0),
        "kwargs": {},
    },

    # Daily sweep (cleanup, backfill) — 8:00 AM UTC
    "daily-sweep-8am-utc": {
        "task": "fin_scraper.jobs.sweep_tasks.run_daily_sweep",
        "schedule": crontab(hour=8, minute=0),
        "kwargs": {},
    },

    # ── Periodic Ingestion ───────────────────────────────────────────────

    # Intraday price ingestion — every 5 min (market hours only for stocks)
    "intraday-prices-every-5-min": {
        "task": "fin_scraper.jobs.price_tasks.ingest_intraday_prices",
        "schedule": crontab(minute="*/5"),
        "kwargs": {},
    },

    # Signal pipeline — every 15 min
    "signal-pipeline-every-15-min": {
        "task": "fin_scraper.jobs.signal_tasks.run_signal_pipeline",
        "schedule": crontab(minute="*/15"),
        "kwargs": {},
    },

    # On-chain metrics — every 15 min
    "onchain-sync-every-15-min": {
        "task": "fin_scraper.jobs.onchain_tasks.sync_onchain_data",
        "schedule": crontab(minute="*/15"),
        "kwargs": {"chain": "ethereum"},
    },

    # Social sentiment — every 30 min
    "social-sentiment-every-30-min": {
        "task": "fin_scraper.jobs.social_tasks.collect_social_sentiment",
        "schedule": crontab(minute="*/30"),
        "kwargs": {},
    },

    # News ingestion — every 30 min
    "news-ingestion-every-30-min": {
        "task": "fin_scraper.jobs.social_tasks.ingest_news",
        "schedule": crontab(minute="15,45"),
        "kwargs": {},
    },

    # Macro economic data — daily at 6:30 AM UTC
    "macro-data-daily-630am-utc": {
        "task": "fin_scraper.jobs.macro_tasks.ingest_macro_data",
        "schedule": crontab(hour=6, minute=30),
        "kwargs": {},
    },
}


# ── Combine all schedules ───────────────────────────────────────────────────

app.conf.beat_schedule = {
    **_always_on_schedule,
    **_scheduled_tasks,
}
