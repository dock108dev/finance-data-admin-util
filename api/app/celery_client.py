"""Celery client for dispatching scraper tasks from the API."""

from __future__ import annotations

from functools import lru_cache

from celery import Celery

from app.config import get_settings


@lru_cache(maxsize=1)
def get_celery_app() -> Celery:
    """Cached Celery instance for task dispatch.

    Same pattern as sports-data-admin/api/app/celery_client.py.
    """
    settings = get_settings()
    app = Celery(
        "fin_scraper",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    app.conf.task_default_queue = "fin-scraper"
    app.conf.task_routes = {
        "fin_scraper.jobs.*": {"queue": "fin-scraper"},
    }
    app.conf.task_always_eager = False
    app.conf.task_eager_propagates = True
    return app
