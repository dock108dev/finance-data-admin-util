"""Finnhub API client — company news, sentiment, earnings calendar."""

from datetime import date, datetime, timezone, timedelta

import httpx
import structlog

from fin_scraper.utils.rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubClient:
    """Thin httpx wrapper for Finnhub API.

    Rate limit: 60 calls/min on free tier.
    Auth: API key as query param.
    """

    def __init__(self, api_key: str, rate_limiter: RateLimiter | None = None):
        self._api_key = api_key
        self._limiter = rate_limiter or RateLimiter(60, 60)
        self._client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    def get_company_news(
        self, symbol: str, from_date: date | None = None, to_date: date | None = None
    ) -> list[dict]:
        """Fetch company news for a stock ticker.

        Args:
            symbol: Stock ticker (e.g. "AAPL").
            from_date: Start date. Defaults to 3 days ago.
            to_date: End date. Defaults to today.

        Returns:
            List of news article dicts.
        """
        if to_date is None:
            to_date = date.today()
        if from_date is None:
            from_date = to_date - timedelta(days=3)

        self._limiter.acquire()

        resp = self._client.get(
            "/company-news",
            params={
                "symbol": symbol,
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
                "token": self._api_key,
            },
        )
        resp.raise_for_status()

        return [
            {
                "title": article["headline"],
                "url": article["url"],
                "source": article.get("source", ""),
                "published_at": datetime.fromtimestamp(
                    article["datetime"], tz=timezone.utc
                ),
                "description": article.get("summary", ""),
                "category": article.get("category", ""),
                "ticker": symbol,
                "sentiment_score": None,  # Finnhub free tier doesn't include sentiment
                "raw_payload": article,
            }
            for article in resp.json()
        ]

    def get_news_sentiment(self, symbol: str) -> dict:
        """Fetch news sentiment aggregation for a ticker.

        Returns:
            Dict with buzz, sentiment scores.
        """
        self._limiter.acquire()

        resp = self._client.get(
            "/news-sentiment",
            params={"symbol": symbol, "token": self._api_key},
        )
        resp.raise_for_status()
        data = resp.json()

        sentiment = data.get("sentiment", {})
        buzz = data.get("buzz", {})

        return {
            "ticker": symbol,
            "bullish_pct": sentiment.get("bullishPercent", 0),
            "bearish_pct": sentiment.get("bearishPercent", 0),
            "articles_in_last_week": buzz.get("articlesInLastWeek", 0),
            "buzz_score": buzz.get("buzz", 0),
            "sector_avg_bullish": data.get("sectorAverageBullishPercent", 0),
            "company_news_score": data.get("companyNewsScore", 0),
        }

    def get_earnings_calendar(
        self, from_date: date | None = None, to_date: date | None = None
    ) -> list[dict]:
        """Fetch upcoming earnings calendar.

        Returns:
            List of earnings event dicts.
        """
        if to_date is None:
            to_date = date.today() + timedelta(days=14)
        if from_date is None:
            from_date = date.today()

        self._limiter.acquire()

        resp = self._client.get(
            "/calendar/earnings",
            params={
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
                "token": self._api_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        return [
            {
                "ticker": ec.get("symbol", ""),
                "date": ec.get("date", ""),
                "eps_estimate": ec.get("epsEstimate"),
                "eps_actual": ec.get("epsActual"),
                "revenue_estimate": ec.get("revenueEstimate"),
                "revenue_actual": ec.get("revenueActual"),
                "hour": ec.get("hour", ""),  # bmo, amc, dmh
            }
            for ec in data.get("earningsCalendar", [])
        ]

    def close(self) -> None:
        self._client.close()
