"""FRED API client — Federal Reserve Economic Data series."""

from datetime import date, timedelta

import httpx
import structlog

from fin_scraper.utils.rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)

BASE_URL = "https://api.stlouisfed.org/fred"

# Tracked FRED series
TRACKED_SERIES: dict[str, dict] = {
    "FEDFUNDS": {"name": "Federal Funds Effective Rate", "category": "interest_rates"},
    "CPIAUCSL": {"name": "Consumer Price Index for All Urban Consumers", "category": "inflation"},
    "GDP": {"name": "Gross Domestic Product", "category": "output"},
    "UNRATE": {"name": "Unemployment Rate", "category": "employment"},
    "T10Y2Y": {"name": "10-Year Treasury Minus 2-Year Treasury", "category": "yield_curve"},
    "VIXCLS": {"name": "CBOE Volatility Index (VIX)", "category": "volatility"},
}


class FredClient:
    """Thin httpx wrapper for FRED API.

    Rate limit: ~120 calls/min (generous for free tier).
    Auth: API key as query param.
    """

    def __init__(self, api_key: str, rate_limiter: RateLimiter | None = None):
        self._api_key = api_key
        self._limiter = rate_limiter or RateLimiter(120, 60)
        self._client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    def get_series_observations(
        self,
        series_id: str,
        observation_start: date | None = None,
        observation_end: date | None = None,
        limit: int = 30,
    ) -> list[dict]:
        """Fetch observations for a FRED series.

        Args:
            series_id: FRED series ID (e.g. "FEDFUNDS").
            observation_start: Start date. Defaults to 90 days ago.
            observation_end: End date. Defaults to today.
            limit: Max observations.

        Returns:
            List of {"date": ..., "value": ...} dicts.
        """
        if observation_end is None:
            observation_end = date.today()
        if observation_start is None:
            observation_start = observation_end - timedelta(days=90)

        self._limiter.acquire()

        resp = self._client.get(
            "/series/observations",
            params={
                "series_id": series_id,
                "api_key": self._api_key,
                "file_type": "json",
                "observation_start": observation_start.isoformat(),
                "observation_end": observation_end.isoformat(),
                "sort_order": "desc",
                "limit": limit,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        observations = []
        series_meta = TRACKED_SERIES.get(series_id, {})

        for obs in data.get("observations", []):
            value_str = obs.get("value", ".")
            if value_str == ".":
                continue  # Missing observation
            observations.append({
                "series_id": series_id,
                "series_name": series_meta.get("name", series_id),
                "category": series_meta.get("category", "unknown"),
                "observation_date": obs["date"],
                "value": float(value_str),
                "source": "fred",
                "raw_data": obs,
            })

        return observations

    def get_all_tracked_series(self, days_back: int = 90) -> list[dict]:
        """Fetch recent observations for all tracked FRED series.

        Returns:
            Flat list of observation dicts across all series.
        """
        all_observations = []
        end = date.today()
        start = end - timedelta(days=days_back)

        for series_id in TRACKED_SERIES:
            try:
                obs = self.get_series_observations(
                    series_id, observation_start=start, observation_end=end
                )
                all_observations.extend(obs)
                logger.info(
                    "fred.series_fetched",
                    series_id=series_id,
                    count=len(obs),
                )
            except Exception as e:
                logger.error(
                    "fred.series_error", series_id=series_id, error=str(e)
                )

        return all_observations

    def close(self) -> None:
        self._client.close()
