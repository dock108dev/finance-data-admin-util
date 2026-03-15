"""On-chain data models — whale wallets, gas, DEX volume.

New for financial context (no direct sports-data-admin equivalent).
Crypto-specific data that feeds into alpha signal generation.
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class WhaleWallet(Base, TimestampMixin):
    """Tracked whale wallet address."""

    __tablename__ = "fin_whale_wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    chain: Mapped[str] = mapped_column(String(20), nullable=False)
    # "ethereum", "bitcoin", "solana"
    label: Mapped[str | None] = mapped_column(String(200))
    # "Binance Cold Wallet", "Unknown Whale #42"
    wallet_type: Mapped[str | None] = mapped_column(String(50))
    # "exchange", "whale", "institution", "defi_protocol"
    balance_usd: Mapped[float | None] = mapped_column(Float)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_whale_wallets_chain", "chain"),
    )


class WhaleTransaction(Base):
    """Significant whale transaction event."""

    __tablename__ = "fin_whale_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_id: Mapped[int | None] = mapped_column(ForeignKey("fin_whale_wallets.id"))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("fin_assets.id"))

    tx_hash: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    chain: Mapped[str] = mapped_column(String(20), nullable=False)
    from_address: Mapped[str] = mapped_column(String(100), nullable=False)
    to_address: Mapped[str] = mapped_column(String(100), nullable=False)

    # Value
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    amount_usd: Mapped[float | None] = mapped_column(Float)
    token_symbol: Mapped[str | None] = mapped_column(String(20))

    # Classification
    tx_type: Mapped[str | None] = mapped_column(String(50))
    # "transfer", "swap", "deposit_exchange", "withdraw_exchange", "contract_call"
    direction: Mapped[str | None] = mapped_column(String(20))
    # "accumulate", "distribute", "internal"

    # Timing
    block_number: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Raw
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("idx_whale_tx_asset", "asset_id"),
        Index("idx_whale_tx_timestamp", "timestamp"),
        Index("idx_whale_tx_type", "tx_type"),
    )


class OnchainMetric(Base):
    """Aggregated on-chain metric snapshot."""

    __tablename__ = "fin_onchain_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("fin_assets.id"), nullable=False)
    chain: Mapped[str] = mapped_column(String(20), nullable=False)

    # Metrics
    active_addresses: Mapped[int | None] = mapped_column(Integer)
    transaction_count: Mapped[int | None] = mapped_column(Integer)
    avg_gas_price: Mapped[float | None] = mapped_column(Float)
    total_fees_usd: Mapped[float | None] = mapped_column(Float)
    dex_volume_usd: Mapped[float | None] = mapped_column(Float)
    tvl_usd: Mapped[float | None] = mapped_column(Float)
    net_exchange_flow: Mapped[float | None] = mapped_column(Float)
    # Positive = deposits (bearish), Negative = withdrawals (bullish)

    # Timing
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_hours: Mapped[int] = mapped_column(Integer, default=24)

    # Raw
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    source: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index("idx_onchain_asset_time", "asset_id", "observed_at"),
    )
