"""Data validation utilities — equivalent to sports-data-admin's validation utils."""

from datetime import datetime


def validate_ticker(ticker: str) -> str:
    """Normalize and validate a ticker symbol."""
    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 20:
        raise ValueError(f"Invalid ticker: {ticker}")
    return ticker


def validate_interval(interval: str) -> str:
    """Validate candle interval string."""
    valid = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"}
    if interval not in valid:
        raise ValueError(f"Invalid interval: {interval}. Must be one of {valid}")
    return interval


def validate_price(price: float, label: str = "price") -> float:
    """Validate a price value is positive and reasonable."""
    if price <= 0:
        raise ValueError(f"{label} must be positive, got {price}")
    return price


def is_market_hours(dt: datetime, asset_class: str) -> bool:
    """Check if a datetime falls within market hours.

    Crypto is 24/7. Stocks are 9:30 AM - 4:00 PM ET (14:30 - 21:00 UTC).
    """
    if asset_class == "CRYPTO":
        return True

    # Stocks: weekday + market hours (simplified UTC check)
    if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    hour_utc = dt.hour + dt.minute / 60
    return 14.5 <= hour_utc < 21.0
