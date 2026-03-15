"""Tests for asset class configuration (STOCKS/CRYPTO configs)."""

import dataclasses

import pytest

from app.config_assets import (
    ASSET_CLASS_CONFIG,
    CRYPTO_CONFIG,
    STOCKS_CONFIG,
    AssetClassConfig,
    get_enabled_asset_classes,
)


class TestStocksConfig:
    def test_code(self):
        assert STOCKS_CONFIG.code == "STOCKS"

    def test_display_name(self):
        assert STOCKS_CONFIG.display_name == "US Equities"

    def test_not_24h(self):
        assert STOCKS_CONFIG.is_24h is False

    def test_onchain_disabled(self):
        assert STOCKS_CONFIG.onchain_enabled is False

    def test_default_exchanges(self):
        assert "NYSE" in STOCKS_CONFIG.default_exchanges
        assert "NASDAQ" in STOCKS_CONFIG.default_exchanges


class TestCryptoConfig:
    def test_code(self):
        assert CRYPTO_CONFIG.code == "CRYPTO"

    def test_is_24h(self):
        assert CRYPTO_CONFIG.is_24h is True

    def test_onchain_enabled(self):
        assert CRYPTO_CONFIG.onchain_enabled is True

    def test_default_exchanges(self):
        assert "Binance" in CRYPTO_CONFIG.default_exchanges
        assert "Coinbase" in CRYPTO_CONFIG.default_exchanges


class TestFrozenDataclass:
    def test_stocks_config_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            STOCKS_CONFIG.code = "MODIFIED"

    def test_crypto_config_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            CRYPTO_CONFIG.code = "MODIFIED"


class TestRegistry:
    def test_contains_stocks(self):
        assert "STOCKS" in ASSET_CLASS_CONFIG

    def test_contains_crypto(self):
        assert "CRYPTO" in ASSET_CLASS_CONFIG

    def test_registry_values_match(self):
        assert ASSET_CLASS_CONFIG["STOCKS"] is STOCKS_CONFIG
        assert ASSET_CLASS_CONFIG["CRYPTO"] is CRYPTO_CONFIG


class TestGetEnabledAssetClasses:
    def test_returns_list(self):
        result = get_enabled_asset_classes()
        assert isinstance(result, list)

    def test_both_enabled_by_default(self):
        result = get_enabled_asset_classes()
        codes = [c.code for c in result]
        assert "STOCKS" in codes
        assert "CRYPTO" in codes

    def test_all_results_are_config_instances(self):
        result = get_enabled_asset_classes()
        for c in result:
            assert isinstance(c, AssetClassConfig)
