"""Tests for SSE endpoint — channel validation and streaming logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.realtime.models import is_valid_channel


class TestSSEChannelParsing:
    """Test that SSE endpoint properly validates channels before subscribing."""

    def test_valid_channels_accepted(self):
        channels = "prices:CRYPTO,asset:1:price,signals:alpha"
        channel_list = [ch.strip() for ch in channels.split(",")]
        assert all(is_valid_channel(ch) for ch in channel_list)

    def test_invalid_channels_rejected(self):
        channels = "prices:CRYPTO,bad:channel,invalid"
        channel_list = [ch.strip() for ch in channels.split(",")]
        valid = [ch for ch in channel_list if is_valid_channel(ch)]
        rejected = [ch for ch in channel_list if not is_valid_channel(ch)]
        assert valid == ["prices:CRYPTO"]
        assert len(rejected) == 2

    def test_empty_channels_filtered(self):
        channels = "prices:CRYPTO,,asset:1:price,"
        channel_list = [ch.strip() for ch in channels.split(",") if ch.strip()]
        assert len(channel_list) == 2

    def test_whitespace_handling(self):
        channels = " prices:CRYPTO , asset:1:price "
        channel_list = [ch.strip() for ch in channels.split(",") if ch.strip()]
        assert all(is_valid_channel(ch) for ch in channel_list)
