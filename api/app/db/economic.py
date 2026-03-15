"""Economic indicators ORM model — FRED macro data."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EconomicIndicator(Base):
    """FRED economic indicator observations (fin_economic_indicators)."""

    __tablename__ = "fin_economic_indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[str] = mapped_column(String(20), nullable=False)
    series_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="fred")
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_econ_indicators_series", "series_id"),
        Index("idx_econ_indicators_date", "observation_date"),
        Index("idx_econ_indicators_category", "category"),
        {"extend_existing": True},
    )
