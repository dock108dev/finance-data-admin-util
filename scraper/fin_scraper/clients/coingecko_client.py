"""CoinGecko API client — OHLC, market data, coin details."""

from datetime import datetime, timezone

import httpx
import structlog

from fin_scraper.utils.rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)

BASE_URL = "https://api.coingecko.com/api/v3"
DEMO_BASE_URL = "https://api.coingecko.com/api/v3"

# Map common tickers to CoinGecko IDs
TICKER_TO_CG_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "LTC": "litecoin",
    "APT": "aptos",
}


class CoinGeckoClient:
    """Thin httpx wrapper for CoinGecko API.

    Rate limit: 30 calls/min on demo key.
    """

    def __init__(self, api_key: str = "", rate_limiter: RateLimiter | None = None):
        self._limiter = rate_limiter or RateLimiter(30, 60)
        headers = {}
        if api_key:
            headers["x-cg-demo-key"] = api_key
        self._client = httpx.Client(base_url=BASE_URL, timeout=15.0, headers=headers)

    def _resolve_id(self, ticker: str, external_ids: dict | None = None) -> str:
        """Resolve ticker to CoinGecko ID."""
        if external_ids and "coingecko_id" in external_ids:
            return external_ids["coingecko_id"]
        return TICKER_TO_CG_ID.get(ticker, ticker.lower())

    def get_ohlc(
        self, ticker: str, days: int = 1, external_ids: dict | None = None
    ) -> list[dict]:
        """Fetch OHLC candles.

        Args:
            ticker: Asset ticker (e.g. "BTC").
            days: 1, 7, 14, 30, 90, 180, 365.
            external_ids: Optional JSONB with coingecko_id.

        Returns:
            List of OHLC candle dicts.
        """
        coin_id = self._resolve_id(ticker, external_ids)
        self._limiter.acquire()

        resp = self._client.get(
            f"/coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": days},
        )
        resp.raise_for_status()

        return [
            {
                "timestamp": datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc),
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": 0,  # OHLC endpoint doesn't include volume
                "interval": "1d" if days >= 30 else "4h" if days >= 2 else "30m",
                "source": "coingecko",
            }
            for row in resp.json()
        ]

    def get_coin_data(self, ticker: str, external_ids: dict | None = None) -> dict:
        """Fetch full coin data (fundamentals, market data).

        Returns:
            Normalized dict with market_cap, supply, tvl, etc.
        """
        coin_id = self._resolve_id(ticker, external_ids)
        self._limiter.acquire()

        resp = self._client.get(
            f"/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        md = data.get("market_data", {})

        return {
            "ticker": ticker,
            "market_cap": md.get("market_cap", {}).get("usd"),
            "fully_diluted_valuation": md.get("fully_diluted_valuation", {}).get("usd"),
            "circulating_supply": md.get("circulating_supply"),
            "max_supply": md.get("max_supply"),
            "total_supply": md.get("total_supply"),
            "tvl": md.get("total_value_locked", {}).get("usd") if md.get("total_value_locked") else None,
            "current_price": md.get("current_price", {}).get("usd"),
            "price_change_24h_pct": md.get("price_change_percentage_24h"),
            "volume_24h": md.get("total_volume", {}).get("usd"),
            "source": "coingecko",
        }

    def get_markets(self, per_page: int = 50) -> list[dict]:
        """Fetch top coins by market cap.

        Returns:
            List of coin market data dicts.
        """
        self._limiter.acquire()

        resp = self._client.get(
            "/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": 1,
                "sparkline": "false",
            },
        )
        resp.raise_for_status()

        return [
            {
                "ticker": coin["symbol"].upper(),
                "coingecko_id": coin["id"],
                "name": coin["name"],
                "price": coin["current_price"],
                "market_cap": coin["market_cap"],
                "volume_24h": coin["total_volume"],
                "price_change_24h_pct": coin["price_change_percentage_24h"],
                "circulating_supply": coin["circulating_supply"],
                "max_supply": coin.get("max_supply"),
            }
            for coin in resp.json()
        ]

    def close(self) -> None:
        self._client.close()
