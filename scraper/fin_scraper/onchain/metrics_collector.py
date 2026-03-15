"""On-chain metrics collector — gas oracle data from Etherscan.

Aggregates gas metrics into fin_onchain_metrics.
"""

from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from fin_scraper.clients.etherscan_client import EtherscanClient

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Collect and persist on-chain metrics from Etherscan."""

    def __init__(self, db_session: Session, etherscan: EtherscanClient):
        self.db = db_session
        self.etherscan = etherscan

    def collect_gas_metrics(self) -> dict:
        """Fetch gas oracle and persist as on-chain metric.

        Returns:
            Summary dict.
        """
        try:
            gas = self.etherscan.get_gas_oracle()
        except Exception as e:
            logger.error("metrics_collector.gas_error", error=str(e))
            return {"error": str(e)}

        # Get ETH asset_id
        result = self.db.execute(
            text(
                "SELECT id FROM fin_assets WHERE ticker = 'ETH' AND asset_class_id = 2"
            )
        )
        row = result.fetchone()
        eth_asset_id = row[0] if row else None

        if eth_asset_id is None:
            logger.warning("metrics_collector.no_eth_asset")
            return {"error": "ETH asset not found"}

        now = datetime.now(timezone.utc)

        self.db.execute(
            text("""
                INSERT INTO fin_onchain_metrics
                    (asset_id, chain, avg_gas_price, observed_at,
                     window_hours, source, raw_data)
                VALUES
                    (:asset_id, 'ethereum', :avg_gas, :observed_at,
                     1, 'etherscan', :raw_data)
            """),
            {
                "asset_id": eth_asset_id,
                "avg_gas": gas["average"],
                "observed_at": now,
                "raw_data": str(gas),
            },
        )
        self.db.commit()

        logger.info(
            "metrics_collector.gas_persisted",
            avg_gas=gas["average"],
            high_gas=gas["high"],
        )
        return {
            "avg_gas": gas["average"],
            "high_gas": gas["high"],
            "base_fee": gas["base_fee"],
        }
