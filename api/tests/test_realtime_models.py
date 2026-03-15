"""Tests for realtime event models and channel validation."""

import time

from app.realtime.models import (
    RealtimeEvent,
    is_valid_channel,
    parse_channel,
)


class TestChannelValidation:
    def test_valid_prices_channel(self):
        assert is_valid_channel("prices:CRYPTO") is True
        assert is_valid_channel("prices:STOCKS") is True

    def test_invalid_prices_channel(self):
        assert is_valid_channel("prices:FOREX") is False
        assert is_valid_channel("prices:") is False
        assert is_valid_channel("prices") is False

    def test_valid_asset_price_channel(self):
        assert is_valid_channel("asset:1:price") is True
        assert is_valid_channel("asset:42:price") is True
        assert is_valid_channel("asset:999:price") is True

    def test_valid_asset_signals_channel(self):
        assert is_valid_channel("asset:1:signals") is True
        assert is_valid_channel("asset:42:signals") is True

    def test_valid_alpha_signals_channel(self):
        assert is_valid_channel("signals:alpha") is True

    def test_valid_sessions_channel(self):
        assert is_valid_channel("sessions:CRYPTO:2024-01-15") is True
        assert is_valid_channel("sessions:STOCKS:2024-12-31") is True

    def test_invalid_sessions_channel(self):
        assert is_valid_channel("sessions:CRYPTO") is False
        assert is_valid_channel("sessions:CRYPTO:bad-date") is False

    def test_invalid_channels(self):
        assert is_valid_channel("") is False
        assert is_valid_channel("unknown:channel") is False
        assert is_valid_channel("asset:abc:price") is False
        assert is_valid_channel("asset::price") is False


class TestParseChannel:
    def test_parse_prices(self):
        result = parse_channel("prices:CRYPTO")
        assert result == {"type": "prices", "asset_class": "CRYPTO"}

    def test_parse_asset_price(self):
        result = parse_channel("asset:42:price")
        assert result == {"type": "asset_price", "asset_id": "42"}

    def test_parse_asset_signals(self):
        result = parse_channel("asset:42:signals")
        assert result == {"type": "asset_signals", "asset_id": "42"}

    def test_parse_alpha_signals(self):
        result = parse_channel("signals:alpha")
        assert result == {"type": "alpha_signals"}

    def test_parse_sessions(self):
        result = parse_channel("sessions:STOCKS:2024-01-15")
        assert result == {
            "type": "sessions",
            "asset_class": "STOCKS",
            "date": "2024-01-15",
        }

    def test_parse_unknown(self):
        result = parse_channel("unknown:channel")
        assert result == {"type": "unknown"}


class TestRealtimeEvent:
    def test_construction(self):
        event = RealtimeEvent(
            type="price_update",
            channel="prices:CRYPTO",
            seq=1,
            payload={"price": 50000.0, "ticker": "BTC"},
        )
        assert event.type == "price_update"
        assert event.channel == "prices:CRYPTO"
        assert event.seq == 1
        assert event.payload["price"] == 50000.0

    def test_to_dict_merges_payload(self):
        event = RealtimeEvent(
            type="price_update",
            channel="prices:CRYPTO",
            seq=5,
            payload={"price": 50000.0, "ticker": "BTC"},
            boot_epoch=1234567890,
        )
        d = event.to_dict()
        assert d["type"] == "price_update"
        assert d["channel"] == "prices:CRYPTO"
        assert d["seq"] == 5
        assert d["price"] == 50000.0
        assert d["ticker"] == "BTC"
        assert d["boot_epoch"] == 1234567890
        assert "ts" in d

    def test_defaults(self):
        event = RealtimeEvent(
            type="test",
            channel="test:ch",
            seq=0,
        )
        assert event.payload == {}
        assert event.boot_epoch == 0
        assert event.ts > 0

    def test_timestamp_is_recent(self):
        before = int(time.time() * 1000)
        event = RealtimeEvent(type="test", channel="test", seq=0)
        after = int(time.time() * 1000)
        assert before <= event.ts <= after
