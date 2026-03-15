"""Whale tracker — monitors large Ethereum transactions from known whale/exchange wallets.

Classifies transactions as exchange deposit (bearish) vs withdrawal (bullish).
"""

from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from fin_scraper.clients.etherscan_client import EtherscanClient

logger = structlog.get_logger(__name__)

# Minimum ETH value to qualify as a "whale" transaction
MIN_WHALE_ETH = 100

# Known exchange deposit addresses (hot wallets)
EXCHANGE_ADDRESSES: dict[str, str] = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance Hot Wallet",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance Hot Wallet 2",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance Hot Wallet 3",
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase Hot Wallet",
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": "Coinbase Hot Wallet 2",
    "0x2910543af39aba0cd09dbb2d50200b3e800a63d2": "Kraken Hot Wallet",
    "0x53d284357ec70ce289d6d64134dfac8e511c8a3d": "Kraken Cold Wallet",
    "0x1db92e2eebc8e0c075a02bea49a2935bcd2dfcf4": "OKX Hot Wallet",
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX Hot Wallet 2",
    "0xf89d7b9c864f589bbf53a82105107622b35eaa40": "Bybit Hot Wallet",
}

# Known whale wallets to monitor
WHALE_WALLETS: list[dict] = [
    {"address": "0x00000000219ab540356cbb839cbe05303d7705fa", "label": "ETH2 Deposit Contract", "type": "whale"},
    {"address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "label": "WETH Contract", "type": "defi_protocol"},
    {"address": "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8", "label": "Binance Cold Wallet", "type": "exchange"},
    {"address": "0xda9dfa130df4de4673b89022ee50ff26f6ea73cf", "label": "Kraken Cold Wallet 2", "type": "exchange"},
    {"address": "0x40b38765696e3d5d8d9d834d8aad4bb6e418e489", "label": "Robinhood", "type": "exchange"},
    {"address": "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0", "label": "Kraken Cold Wallet 3", "type": "exchange"},
]


class WhaleTracker:
    """Track whale transactions on Ethereum via Etherscan."""

    def __init__(self, db_session: Session, etherscan: EtherscanClient):
        self.db = db_session
        self.etherscan = etherscan

    def scan_whale_transactions(self) -> dict:
        """Scan known whale wallets for large transactions.

        Returns:
            Summary dict with transaction counts.
        """
        results = {"wallets_scanned": 0, "transactions_found": 0, "whale_txns_persisted": 0}

        # Ensure whale wallets are in the database
        self._ensure_wallets_exist()

        all_addresses = list(EXCHANGE_ADDRESSES.keys()) + [w["address"] for w in WHALE_WALLETS]

        for address in all_addresses:
            try:
                txns = self.etherscan.get_normal_transactions(address, page=1, offset=20)
                results["wallets_scanned"] += 1

                for tx in txns:
                    if tx["amount"] < MIN_WHALE_ETH:
                        continue

                    direction = self._classify_direction(tx, address)
                    tx_type = self._classify_tx_type(tx, address)

                    self._persist_transaction(tx, address, direction, tx_type)
                    results["transactions_found"] += 1

                results["whale_txns_persisted"] = results["transactions_found"]

            except Exception as e:
                logger.error(
                    "whale_tracker.scan_error",
                    address=address[:10],
                    error=str(e),
                )

        self.db.commit()
        logger.info("whale_tracker.scan_complete", **results)
        return results

    def compute_exchange_flows(self) -> dict:
        """Compute net exchange flow from recent whale transactions.

        Positive = deposits (bearish), Negative = withdrawals (bullish).
        """
        result = self.db.execute(
            text("""
                SELECT
                    SUM(CASE WHEN direction = 'distribute' THEN amount_usd ELSE 0 END) as deposits,
                    SUM(CASE WHEN direction = 'accumulate' THEN amount_usd ELSE 0 END) as withdrawals
                FROM fin_whale_transactions
                WHERE timestamp > NOW() - INTERVAL '1 hour'
            """)
        )
        row = result.fetchone()
        deposits = row[0] or 0 if row else 0
        withdrawals = row[1] or 0 if row else 0

        return {
            "net_flow": deposits - withdrawals,
            "deposits": deposits,
            "withdrawals": withdrawals,
            "signal": "bearish" if deposits > withdrawals else "bullish",
        }

    def _classify_direction(self, tx: dict, monitored_address: str) -> str:
        """Classify if this is accumulation or distribution."""
        from_addr = tx["from_address"].lower()
        to_addr = tx["to_address"].lower()
        monitored = monitored_address.lower()

        # If money flows TO an exchange → bearish (selling/distributing)
        if to_addr in EXCHANGE_ADDRESSES:
            return "distribute"
        # If money flows FROM an exchange → bullish (buying/accumulating)
        if from_addr in EXCHANGE_ADDRESSES:
            return "accumulate"
        # If the monitored wallet is receiving → accumulating
        if to_addr == monitored:
            return "accumulate"
        return "distribute"

    def _classify_tx_type(self, tx: dict, monitored_address: str) -> str:
        """Classify transaction type."""
        from_addr = tx["from_address"].lower()
        to_addr = tx["to_address"].lower()

        if to_addr in EXCHANGE_ADDRESSES:
            return "deposit_exchange"
        if from_addr in EXCHANGE_ADDRESSES:
            return "withdraw_exchange"
        return "transfer"

    def _persist_transaction(
        self, tx: dict, wallet_address: str, direction: str, tx_type: str
    ) -> None:
        """Persist a whale transaction."""
        # Get or create wallet_id
        wallet_result = self.db.execute(
            text("SELECT id FROM fin_whale_wallets WHERE address = :addr"),
            {"addr": wallet_address},
        )
        wallet_row = wallet_result.fetchone()
        wallet_id = wallet_row[0] if wallet_row else None

        # Estimate USD value (rough: ETH * $3000 placeholder)
        amount_usd = tx["amount"] * 3000  # Will be replaced with live price

        self.db.execute(
            text("""
                INSERT INTO fin_whale_transactions
                    (wallet_id, tx_hash, chain, from_address, to_address,
                     amount, amount_usd, token_symbol, tx_type, direction,
                     block_number, timestamp)
                VALUES
                    (:wallet_id, :tx_hash, 'ethereum', :from_addr, :to_addr,
                     :amount, :amount_usd, :token_symbol, :tx_type, :direction,
                     :block_number, :timestamp)
                ON CONFLICT (tx_hash) DO NOTHING
            """),
            {
                "wallet_id": wallet_id,
                "tx_hash": tx["tx_hash"],
                "from_addr": tx["from_address"],
                "to_addr": tx["to_address"],
                "amount": tx["amount"],
                "amount_usd": amount_usd,
                "token_symbol": tx.get("token_symbol", "ETH"),
                "tx_type": tx_type,
                "direction": direction,
                "block_number": tx.get("block_number", 0),
                "timestamp": tx.get("timestamp", datetime.now(timezone.utc)),
            },
        )

    def _ensure_wallets_exist(self) -> None:
        """Ensure all tracked wallets are in the database."""
        # Exchange wallets
        for address, label in EXCHANGE_ADDRESSES.items():
            self.db.execute(
                text("""
                    INSERT INTO fin_whale_wallets (address, chain, label, wallet_type)
                    VALUES (:address, 'ethereum', :label, 'exchange')
                    ON CONFLICT (address) DO NOTHING
                """),
                {"address": address, "label": label},
            )

        # Whale wallets
        for wallet in WHALE_WALLETS:
            self.db.execute(
                text("""
                    INSERT INTO fin_whale_wallets (address, chain, label, wallet_type)
                    VALUES (:address, 'ethereum', :label, :wallet_type)
                    ON CONFLICT (address) DO NOTHING
                """),
                {
                    "address": wallet["address"],
                    "label": wallet["label"],
                    "wallet_type": wallet["type"],
                },
            )

        self.db.commit()
