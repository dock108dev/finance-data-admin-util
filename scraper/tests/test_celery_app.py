"""Tests for Celery app configuration and beat schedule."""

from fin_scraper.celery_app import app


class TestCeleryApp:
    def test_app_name(self):
        assert app.main == "fin_scraper"

    def test_serializer(self):
        assert app.conf.task_serializer == "json"

    def test_timezone(self):
        assert app.conf.timezone == "UTC"

    def test_enable_utc(self):
        assert app.conf.enable_utc is True

    def test_default_queue(self):
        assert app.conf.task_default_queue == "fin-scraper"


class TestBeatSchedule:
    def test_has_exchange_sync(self):
        assert "exchange-price-sync-every-1-min" in app.conf.beat_schedule

    def test_has_daily_price(self):
        assert "daily-price-ingestion-5am-utc" in app.conf.beat_schedule

    def test_has_signal_pipeline(self):
        assert "signal-pipeline-every-15-min" in app.conf.beat_schedule

    def test_has_daily_sweep(self):
        assert "daily-sweep-8am-utc" in app.conf.beat_schedule

    def test_has_social_sentiment(self):
        assert "social-sentiment-every-30-min" in app.conf.beat_schedule

    def test_has_onchain_sync(self):
        assert "onchain-sync-every-15-min" in app.conf.beat_schedule

    def test_schedule_count(self):
        # 1 always-on + 9 scheduled = 10 total
        assert len(app.conf.beat_schedule) == 10


class TestTaskRouting:
    def test_jobs_route_to_queue(self):
        routes = app.conf.task_routes
        assert "fin_scraper.jobs.*" in routes
        assert routes["fin_scraper.jobs.*"]["queue"] == "fin-scraper"
