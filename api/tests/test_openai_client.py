"""Tests for the OpenAI client — narrative generation and flow pass."""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.openai_client import (
    generate_market_narrative,
    apply_flow_pass,
    strip_forbidden_language,
    _build_narrative_prompt,
    FORBIDDEN_PHRASES,
)


class TestStripForbiddenLanguage:
    def test_removes_forbidden_phrases(self):
        text = "The stock is rising. You should buy now before it's too late."
        result = strip_forbidden_language(text)
        assert "you should buy" not in result.lower()

    def test_preserves_clean_text(self):
        text = "The session closed with strong volume near the day's highs."
        result = strip_forbidden_language(text)
        assert result == text

    def test_case_insensitive(self):
        text = "This is NOT FINANCIAL ADVICE but the stock looks good."
        result = strip_forbidden_language(text)
        assert "financial advice" not in result.lower()

    def test_multiple_forbidden_phrases(self):
        text = "Guaranteed profit! Buy now for risk-free returns."
        result = strip_forbidden_language(text)
        assert "guaranteed profit" not in result.lower()
        assert "risk-free" not in result.lower()


class TestBuildNarrativePrompt:
    def test_includes_session_data(self):
        prompt = _build_narrative_prompt(
            candle_summary={"open": 100, "high": 105, "low": 98, "close": 103, "volume": 50000, "change_pct": 3.0, "candle_count": 40},
            events=[],
            sentiment={},
            indicators={},
        )
        assert "100" in prompt
        assert "105" in prompt
        assert "3.0%" in prompt

    def test_includes_events(self):
        prompt = _build_narrative_prompt(
            candle_summary={"open": 100},
            events=[{"event_type": "VOLUME_SPIKE", "description": "Big spike", "price": 105, "volume": 90000}],
            sentiment={},
            indicators={},
        )
        assert "VOLUME_SPIKE" in prompt
        assert "Big spike" in prompt

    def test_includes_sentiment(self):
        prompt = _build_narrative_prompt(
            candle_summary={"open": 100},
            events=[],
            sentiment={"sentiment_score": 0.5, "social_posts": 10, "news_articles": 5, "fear_greed_index": 72},
            indicators={},
        )
        assert "0.5" in prompt
        assert "72" in prompt

    def test_includes_indicators(self):
        prompt = _build_narrative_prompt(
            candle_summary={"open": 100},
            events=[],
            sentiment={},
            indicators={"rsi_14": 45.5, "macd_histogram": 0.23},
        )
        assert "rsi_14" in prompt
        assert "45.5" in prompt


class TestGenerateMarketNarrative:
    @pytest.mark.asyncio
    async def test_generates_blocks_from_openai(self):
        mock_response = {
            "blocks": [
                {"role": "SETUP", "narrative": "The market opened cautiously amid mixed signals from overnight futures."},
                {"role": "CATALYST", "narrative": "A strong earnings beat sparked buying interest."},
                {"role": "RESOLUTION", "narrative": "The session closed at session highs with heavy volume."},
            ]
        }

        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(mock_response)}}]
        }

        with patch("app.services.openai_client.get_settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_class:
            mock_settings.return_value.openai_api_key = "test-key"
            mock_settings.return_value.openai_model_analysis = "gpt-4o"

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_http_response)
            mock_client_class.return_value = mock_client

            result = await generate_market_narrative(
                candle_summary={"open": 100, "close": 103},
                events=[],
                sentiment={},
                indicators={},
            )

            assert len(result) == 3
            assert result[0]["role"] == "SETUP"
            assert result[2]["role"] == "RESOLUTION"
            assert all("word_count" in b for b in result)

    @pytest.mark.asyncio
    async def test_raises_on_missing_api_key(self):
        with patch("app.services.openai_client.get_settings") as mock_settings:
            mock_settings.return_value.openai_api_key = ""

            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                await generate_market_narrative(
                    candle_summary={},
                    events=[],
                    sentiment={},
                    indicators={},
                )

    @pytest.mark.asyncio
    async def test_strips_forbidden_language_from_blocks(self):
        mock_response = {
            "blocks": [
                {"role": "SETUP", "narrative": "You should buy this stock. Not financial advice."},
                {"role": "RESOLUTION", "narrative": "Clean closing narrative here."},
            ]
        }

        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(mock_response)}}]
        }

        with patch("app.services.openai_client.get_settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_class:
            mock_settings.return_value.openai_api_key = "test-key"
            mock_settings.return_value.openai_model_analysis = "gpt-4o"

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_http_response)
            mock_client_class.return_value = mock_client

            result = await generate_market_narrative(
                candle_summary={},
                events=[],
                sentiment={},
                indicators={},
            )

            # Should have stripped forbidden phrases
            assert "you should buy" not in result[0]["narrative"].lower()
            assert "financial advice" not in result[0]["narrative"].lower()


class TestApplyFlowPass:
    @pytest.mark.asyncio
    async def test_returns_original_on_empty(self):
        result = await apply_flow_pass([], asset_context="AAPL")
        assert result == []

    @pytest.mark.asyncio
    async def test_smooths_blocks(self):
        input_blocks = [
            {"role": "SETUP", "narrative": "Market opened flat.", "word_count": 3},
            {"role": "RESOLUTION", "narrative": "Market closed higher.", "word_count": 3},
        ]

        smoothed = [
            {"role": "SETUP", "narrative": "The market opened on a flat note.", "word_count": 7},
            {"role": "RESOLUTION", "narrative": "By close, the market had moved higher.", "word_count": 8},
        ]

        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({"blocks": smoothed})}}]
        }

        with patch("app.services.openai_client.get_settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_class:
            mock_settings.return_value.openai_api_key = "test-key"
            mock_settings.return_value.openai_model_analysis = "gpt-4o"

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_http_response)
            mock_client_class.return_value = mock_client

            result = await apply_flow_pass(input_blocks, asset_context="AAPL (Apple Inc.)")

            assert len(result) == 2
            assert result[0]["role"] == "SETUP"
            assert result[0]["word_count"] > 0
