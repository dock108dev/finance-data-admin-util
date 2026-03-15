"""On-chain data ingestion tasks — whale tracking, gas metrics.

Tasks:
    sync_onchain_data  — Fetch whale transactions + gas oracle from Etherscan
"""

import structlog
from celery import shared_task

from fin_scraper.db import get_db_session
from fin_scraper.services.run_manager import create_run, complete_run, fail_run

logger = structlog.get_logger(__name__)


@shared_task(name="fin_scraper.jobs.onchain_tasks.sync_onchain_data")
def sync_onchain_data(chain: str = "ethereum") -> dict:
    """Sync on-chain metrics — whale wallets, gas prices.

    Sources: Etherscan API (whale transactions, gas oracle).

    Feeds into alpha signal generation:
    - Whale accumulation → bullish signal
    - Exchange outflows → bullish (coins leaving exchanges)
    - High gas → increased activity / congestion
    """
    with get_db_session() as db:
        run = create_run(db, "onchain_sync", requested_by="celery_beat")
        try:
            logger.info("onchain_sync.start", chain=chain)

            from fin_scraper.config import get_settings
            from fin_scraper.clients.etherscan_client import EtherscanClient
            from fin_scraper.onchain.whale_tracker import WhaleTracker
            from fin_scraper.onchain.metrics_collector import MetricsCollector

            settings = get_settings()
            if not settings.etherscan_api_key:
                logger.warning("onchain_sync.no_etherscan_key")
                complete_run(db, run, summary="no API key")
                return {"whale_transactions": 0, "metrics_updated": 0}

            etherscan = EtherscanClient(api_key=settings.etherscan_api_key)

            results = {
                "whale_transactions": 0,
                "metrics_updated": 0,
                "wallets_scanned": 0,
            }

            # Whale transaction scanning
            try:
                tracker = WhaleTracker(db, etherscan)
                whale_results = tracker.scan_whale_transactions()
                results["whale_transactions"] = whale_results.get("transactions_found", 0)
                results["wallets_scanned"] = whale_results.get("wallets_scanned", 0)
            except Exception as e:
                logger.error("onchain_sync.whale_error", error=str(e))

            # Gas metrics
            try:
                metrics = MetricsCollector(db, etherscan)
                gas_result = metrics.collect_gas_metrics()
                if "error" not in gas_result:
                    results["metrics_updated"] += 1
            except Exception as e:
                logger.error("onchain_sync.metrics_error", error=str(e))

            etherscan.close()
            complete_run(db, run, summary=str(results))
            logger.info("onchain_sync.complete", **results)
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            logger.error("onchain_sync.failed", error=str(e))
            raise
