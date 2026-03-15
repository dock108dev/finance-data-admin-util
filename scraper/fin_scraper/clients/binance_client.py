"""Binance public API client — klines, spot prices, book tickers."""

from datetime import datetime, timezone

import httpx
import structlog

from fin_scraper.utils.rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)

BASE_URL = "https://api.binance.com"


class BinanceClient:
    """Thin httpx wrapper for Binance public endpoints.

    Rate limit: 1200 request weight/min (public endpoints are weight=1 each).
    No auth needed for public data.
    """

    # Map common crypto tickers to Binance trading pairs
    PAIR_MAP: dict[str, str] = {
        "BTC": "BTCUSDT",
        "ETH": "ETHUSDT",
        "BNB": "BNBUSDT",
        "SOL": "SOLUSDT",
        "XRP": "XRPUSDT",
        "ADA": "ADAUSDT",
        "DOGE": "DOGEUSDT",
        "AVAX": "AVAXUSDT",
        "DOT": "DOTUSDT",
        "MATIC": "MATICUSDT",
        "LINK": "LINKUSDT",
        "UNI": "UNIUSDT",
        "ATOM": "ATOMUSDT",
        "LTC": "LTCUSDT",
        "APT": "APTUSDT",
    }

    def __init__(self, rate_limiter: RateLimiter | None = None):
        self._limiter = rate_limiter or RateLimiter(1200, 60)
        self._client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    def get_klines(
        self, symbol: str, interval: str = "1d", limit: int = 100
    ) -> list[dict]:
        """Fetch kline/candlestick data.

        Args:
            symbol: Ticker (e.g. "BTC") or full pair (e.g. "BTCUSDT").
            interval: Candle interval (1m, 5m, 15m, 1h, 1d).
            limit: Number of candles (max 1000).

        Returns:
            List of normalized candle dicts.
        """
        pair = self.PAIR_MAP.get(symbol, symbol)
        self._limiter.acquire()

        resp = self._client.get(
            "/api/v3/klines",
            params={"symbol": pair, "interval": interval, "limit": limit},
        )
        resp.raise_for_status()

        return [
            {
                "timestamp": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "trade_count": int(k[8]),
                "interval": interval,
                "source": "binance",
            }
            for k in resp.json()
        ]

    def get_ticker_price(self, symbol: str) -> dict:
        """Get latest spot price for a symbol.

        Returns:
            {"symbol": "BTCUSDT", "price": 65432.10}
        """
        pair = self.PAIR_MAP.get(symbol, symbol)
        self._limiter.acquire()

        resp = self._client.get("/api/v3/ticker/price", params={"symbol": pair})
        resp.raise_for_status()
        data = resp.json()

        return {
            "symbol": symbol,
            "pair": pair,
            "price": float(data["price"]),
            "exchange": "Binance",
            "observed_at": datetime.now(timezone.utc),
        }

    def get_book_ticker(self, symbol: str) -> dict:
        """Get best bid/ask for a symbol.

        Returns:
            {"symbol": ..., "bid": ..., "ask": ..., "spread": ...}
        """
        pair = self.PAIR_MAP.get(symbol, symbol)
        self._limiter.acquire()

        resp = self._client.get("/api/v3/ticker/bookTicker", params={"symbol": pair})
        resp.raise_for_status()
        data = resp.json()

        bid = float(data["bidPrice"])
        ask = float(data["askPrice"])
        mid = (bid + ask) / 2 if bid and ask else 0

        return {
            "symbol": symbol,
            "pair": pair,
            "bid": bid,
            "ask": ask,
            "spread": ask - bid,
            "spread_pct": ((ask - bid) / mid * 100) if mid else 0,
            "exchange": "Binance",
            "observed_at": datetime.now(timezone.utc),
        }

    def get_24h_ticker(self, symbol: str) -> dict:
        """Get 24h price change statistics."""
        pair = self.PAIR_MAP.get(symbol, symbol)
        self._limiter.acquire()

        resp = self._client.get("/api/v3/ticker/24hr", params={"symbol": pair})
        resp.raise_for_status()
        data = resp.json()

        return {
            "symbol": symbol,
            "price": float(data["lastPrice"]),
            "bid": float(data["bidPrice"]),
            "ask": float(data["askPrice"]),
            "volume_24h": float(data["quoteVolume"]),
            "price_change_pct": float(data["priceChangePercent"]),
            "exchange": "Binance",
            "observed_at": datetime.now(timezone.utc),
        }

    def close(self) -> None:
        self._client.close()
