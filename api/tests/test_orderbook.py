"""Tests for the order book module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scraper"))

from fin_scraper.orderbook import (
    OrderBookLevel,
    OrderBookSnapshot,
    create_snapshot,
    compute_depth,
)


class TestOrderBookSnapshot:
    def test_computed_fields(self):
        snapshot = create_snapshot(
            asset_id=1,
            exchange="Binance",
            bids=[(100.0, 10.0), (99.0, 20.0)],
            asks=[(101.0, 15.0), (102.0, 25.0)],
        )
        assert snapshot.mid_price == 100.5
        assert snapshot.spread == 1.0
        assert snapshot.spread_pct > 0

    def test_empty_order_book(self):
        snapshot = create_snapshot(
            asset_id=1,
            exchange="Coinbase",
            bids=[],
            asks=[],
        )
        assert snapshot.mid_price is None
        assert snapshot.spread is None

    def test_timestamp_set(self):
        snapshot = create_snapshot(1, "Binance", [(100, 1)], [(101, 1)])
        assert snapshot.timestamp is not None


class TestComputeDepth:
    def test_balanced_book(self):
        snapshot = create_snapshot(
            asset_id=1,
            exchange="Test",
            bids=[(100.0, 10.0), (99.5, 20.0)],
            asks=[(100.5, 10.0), (101.0, 20.0)],
        )
        depth = compute_depth(snapshot, pct_from_mid=1.0)
        assert depth["bid_depth"] > 0
        assert depth["ask_depth"] > 0
        assert -1 <= depth["imbalance"] <= 1

    def test_empty_book(self):
        snapshot = create_snapshot(1, "Test", [], [])
        depth = compute_depth(snapshot)
        assert depth["bid_depth"] == 0
        assert depth["ask_depth"] == 0
        assert depth["imbalance"] == 0

    def test_bid_heavy_book(self):
        snapshot = create_snapshot(
            asset_id=1,
            exchange="Test",
            bids=[(100.0, 100.0)],
            asks=[(100.5, 10.0)],
        )
        depth = compute_depth(snapshot, pct_from_mid=5.0)
        assert depth["imbalance"] > 0  # Bid heavy = positive imbalance
