"""Check if US stock market is currently open (9:30 AM – 4:00 PM ET, weekdays)."""

from datetime import datetime, timezone, timedelta

# US Eastern offset: UTC-5 (EST) or UTC-4 (EDT)
# Simplified: we use America/New_York via manual offset calculation.
_ET_OFFSET_STANDARD = timedelta(hours=-5)
_ET_OFFSET_DST = timedelta(hours=-4)

# Market hours in ET
_MARKET_OPEN_HOUR = 9
_MARKET_OPEN_MINUTE = 30
_MARKET_CLOSE_HOUR = 16
_MARKET_CLOSE_MINUTE = 0


def _is_dst(dt_utc: datetime) -> bool:
    """Rough DST check for US Eastern (second Sunday of March to first Sunday of November)."""
    year = dt_utc.year
    # March: second Sunday
    march_first = datetime(year, 3, 1, tzinfo=timezone.utc)
    march_second_sunday = 14 - march_first.weekday() % 7
    if march_first.weekday() == 6:
        march_second_sunday = 8
    else:
        march_second_sunday = 8 + (6 - march_first.weekday()) % 7
    dst_start = datetime(year, 3, march_second_sunday, 7, tzinfo=timezone.utc)  # 2 AM ET = 7 AM UTC

    # November: first Sunday
    nov_first = datetime(year, 11, 1, tzinfo=timezone.utc)
    if nov_first.weekday() == 6:
        nov_first_sunday = 1
    else:
        nov_first_sunday = 1 + (6 - nov_first.weekday()) % 7
    dst_end = datetime(year, 11, nov_first_sunday, 6, tzinfo=timezone.utc)  # 2 AM ET = 6 AM UTC

    return dst_start <= dt_utc < dst_end


def _to_et(dt_utc: datetime) -> datetime:
    """Convert UTC datetime to US Eastern."""
    offset = _ET_OFFSET_DST if _is_dst(dt_utc) else _ET_OFFSET_STANDARD
    return dt_utc + offset


def is_market_open(dt_utc: datetime | None = None) -> bool:
    """Check if the US stock market is open at the given UTC time.

    Args:
        dt_utc: UTC datetime to check. Defaults to now.

    Returns:
        True if market is open (weekday, 9:30 AM - 4:00 PM ET).
        Does NOT account for holidays.
    """
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)

    et = _to_et(dt_utc)

    # Weekday check (Monday=0 through Friday=4)
    if et.weekday() >= 5:
        return False

    # Time check
    market_open = et.replace(hour=_MARKET_OPEN_HOUR, minute=_MARKET_OPEN_MINUTE, second=0, microsecond=0)
    market_close = et.replace(hour=_MARKET_CLOSE_HOUR, minute=_MARKET_CLOSE_MINUTE, second=0, microsecond=0)

    return market_open <= et < market_close
