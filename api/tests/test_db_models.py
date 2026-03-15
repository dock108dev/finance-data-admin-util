"""Tests for ORM models — verify table names, columns, constraints, indexes."""

import pytest

from app.db.base import Base, TimestampMixin
from app.db.markets import (
    Asset,
    AssetClass,
    AssetFundamental,
    Candle,
    MarketSession,
    SessionSummary,
)
from app.db.exchanges import ArbitrageWork, ExchangePrice
from app.db.signals import AlphaSignal, MarketAnalysis, SessionTimeline
from app.db.social import (
    NewsArticle,
    SentimentSnapshot,
    SocialAccount,
    SocialPost,
)
from app.db.scraper import DataConflict, JobRun, ScrapeRun
from app.db.onchain import OnchainMetric, WhaleTransaction, WhaleWallet


class TestBase:
    def test_base_is_declarative(self):
        assert hasattr(Base, "metadata")

    def test_timestamp_mixin_has_created_at(self):
        assert hasattr(TimestampMixin, "created_at")

    def test_timestamp_mixin_has_updated_at(self):
        assert hasattr(TimestampMixin, "updated_at")


class TestAssetClass:
    def test_tablename(self):
        assert AssetClass.__tablename__ == "fin_asset_classes"

    def test_has_id_column(self):
        assert "id" in AssetClass.__table__.columns.keys()

    def test_has_code_column(self):
        assert "code" in AssetClass.__table__.columns.keys()

    def test_code_is_unique(self):
        col = AssetClass.__table__.columns["code"]
        assert col.unique is True


class TestAsset:
    def test_tablename(self):
        assert Asset.__tablename__ == "fin_assets"

    def test_has_required_columns(self):
        cols = Asset.__table__.columns.keys()
        for expected in ["id", "asset_class_id", "ticker", "name", "is_active"]:
            assert expected in cols

    def test_has_unique_constraint(self):
        constraints = [c.name for c in Asset.__table__.constraints if hasattr(c, "name") and c.name]
        assert "uq_asset_class_ticker" in constraints

    def test_has_indexes(self):
        index_names = [i.name for i in Asset.__table__.indexes]
        assert "idx_assets_ticker" in index_names
        assert "idx_assets_class_active" in index_names


class TestMarketSession:
    def test_tablename(self):
        assert MarketSession.__tablename__ == "fin_sessions"

    def test_has_ohlcv_columns(self):
        cols = MarketSession.__table__.columns.keys()
        for c in ["open_price", "high_price", "low_price", "close_price", "volume"]:
            assert c in cols

    def test_has_status_column(self):
        assert "status" in MarketSession.__table__.columns.keys()


class TestCandle:
    def test_tablename(self):
        assert Candle.__tablename__ == "fin_candles"

    def test_has_ohlcv_columns(self):
        cols = Candle.__table__.columns.keys()
        for c in ["open", "high", "low", "close", "volume"]:
            assert c in cols

    def test_has_unique_constraint(self):
        constraints = [c.name for c in Candle.__table__.constraints if hasattr(c, "name") and c.name]
        assert "uq_candle_identity" in constraints


class TestSessionSummary:
    def test_tablename(self):
        assert SessionSummary.__tablename__ == "fin_session_summaries"

    def test_has_technical_columns(self):
        cols = SessionSummary.__table__.columns.keys()
        for c in ["rsi_14", "macd_signal", "bb_upper", "bb_lower"]:
            assert c in cols


class TestAssetFundamental:
    def test_tablename(self):
        assert AssetFundamental.__tablename__ == "fin_asset_fundamentals"

    def test_has_stock_and_crypto_columns(self):
        cols = AssetFundamental.__table__.columns.keys()
        assert "pe_ratio" in cols
        assert "tvl" in cols


class TestExchangePrice:
    def test_tablename(self):
        assert ExchangePrice.__tablename__ == "fin_exchange_prices"

    def test_has_price_columns(self):
        cols = ExchangePrice.__table__.columns.keys()
        for c in ["price", "bid", "ask", "spread"]:
            assert c in cols


class TestArbitrageWork:
    def test_tablename(self):
        assert ArbitrageWork.__tablename__ == "fin_arbitrage_work"

    def test_composite_pk(self):
        pk_cols = [c.name for c in ArbitrageWork.__table__.primary_key.columns]
        assert "asset_id" in pk_cols
        assert "pair_key" in pk_cols
        assert "exchange" in pk_cols


class TestAlphaSignal:
    def test_tablename(self):
        assert AlphaSignal.__tablename__ == "fin_alpha_signals"

    def test_has_signal_columns(self):
        cols = AlphaSignal.__table__.columns.keys()
        for c in ["signal_type", "direction", "strength", "confidence_tier"]:
            assert c in cols


class TestMarketAnalysis:
    def test_tablename(self):
        assert MarketAnalysis.__tablename__ == "fin_market_analyses"


class TestSessionTimeline:
    def test_tablename(self):
        assert SessionTimeline.__tablename__ == "fin_session_timelines"


class TestSocialPost:
    def test_tablename(self):
        assert SocialPost.__tablename__ == "fin_social_posts"

    def test_has_sentiment_columns(self):
        cols = SocialPost.__table__.columns.keys()
        assert "sentiment_score" in cols
        assert "sentiment_label" in cols


class TestSocialAccount:
    def test_tablename(self):
        assert SocialAccount.__tablename__ == "fin_social_accounts"


class TestSentimentSnapshot:
    def test_tablename(self):
        assert SentimentSnapshot.__tablename__ == "fin_sentiment_snapshots"


class TestNewsArticle:
    def test_tablename(self):
        assert NewsArticle.__tablename__ == "fin_news_articles"


class TestScrapeRun:
    def test_tablename(self):
        assert ScrapeRun.__tablename__ == "fin_scrape_runs"


class TestJobRun:
    def test_tablename(self):
        assert JobRun.__tablename__ == "fin_job_runs"


class TestDataConflict:
    def test_tablename(self):
        assert DataConflict.__tablename__ == "fin_data_conflicts"


class TestWhaleWallet:
    def test_tablename(self):
        assert WhaleWallet.__tablename__ == "fin_whale_wallets"

    def test_address_unique(self):
        col = WhaleWallet.__table__.columns["address"]
        assert col.unique is True


class TestWhaleTransaction:
    def test_tablename(self):
        assert WhaleTransaction.__tablename__ == "fin_whale_transactions"

    def test_tx_hash_unique(self):
        col = WhaleTransaction.__table__.columns["tx_hash"]
        assert col.unique is True


class TestOnchainMetric:
    def test_tablename(self):
        assert OnchainMetric.__tablename__ == "fin_onchain_metrics"

    def test_has_metric_columns(self):
        cols = OnchainMetric.__table__.columns.keys()
        for c in ["active_addresses", "dex_volume_usd", "tvl_usd", "net_exchange_flow"]:
            assert c in cols
