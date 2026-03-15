"""Analytics models — ML models, feature configs, training jobs, backtests.

Equivalent to sports-data-admin's db/analytics.py.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MLModel(Base, TimestampMixin):
    """ML model metadata and versioning."""

    __tablename__ = "fin_ml_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # "signal_classifier", "price_predictor", "regime_detector", "sentiment_scorer"
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    asset_class: Mapped[str | None] = mapped_column(String(20))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_production: Mapped[bool] = mapped_column(Boolean, default=False)

    # Model metadata
    description: Mapped[str | None] = mapped_column(Text)
    hyperparameters: Mapped[dict | None] = mapped_column(JSONB)
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    # {"accuracy": 0.85, "precision": 0.82, "recall": 0.78, "f1": 0.80}
    artifact_path: Mapped[str | None] = mapped_column(String(500))

    # Training info
    training_samples: Mapped[int | None] = mapped_column(Integer)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_name_version"),
        Index("idx_models_type", "model_type"),
        Index("idx_models_active", "is_active"),
    )


class FeatureConfig(Base, TimestampMixin):
    """Feature configuration for ML models — defines input features."""

    __tablename__ = "fin_feature_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_class: Mapped[str | None] = mapped_column(String(20))

    # Feature list
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {"technical": ["rsi_14", "macd_hist", "bb_position"], "sentiment": ["fear_greed", "social_volume"]}

    # Preprocessing
    scaler_type: Mapped[str | None] = mapped_column(String(30))
    # "standard", "minmax", "robust"
    lookback_periods: Mapped[int] = mapped_column(Integer, default=30)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("idx_feature_configs_type", "model_type"),
    )


class TrainingJob(Base, TimestampMixin):
    """ML model training job execution record."""

    __tablename__ = "fin_training_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("fin_ml_models.id"))
    feature_config_id: Mapped[int | None] = mapped_column(ForeignKey("fin_feature_configs.id"))

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # "pending", "running", "completed", "failed"

    # Parameters
    training_params: Mapped[dict | None] = mapped_column(JSONB)
    dataset_size: Mapped[int | None] = mapped_column(Integer)

    # Results
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    error_details: Mapped[str | None] = mapped_column(Text)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        Index("idx_training_jobs_status", "status"),
        Index("idx_training_jobs_model", "model_id"),
    )


class BacktestJob(Base, TimestampMixin):
    """Signal backtesting job — tests signals against historical data."""

    __tablename__ = "fin_backtest_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    signal_type: Mapped[str | None] = mapped_column(String(50))
    asset_class: Mapped[str | None] = mapped_column(String(20))

    # Parameters
    start_date: Mapped[str | None] = mapped_column(String(10))
    end_date: Mapped[str | None] = mapped_column(String(10))
    params: Mapped[dict | None] = mapped_column(JSONB)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    # Results
    results: Mapped[dict | None] = mapped_column(JSONB)
    # {"total_signals": 150, "hit_rate": 0.62, "avg_return": 1.3, "sharpe": 1.8}

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_backtest_status", "status"),
    )


class PredictionOutcome(Base, TimestampMixin):
    """Prediction vs actual outcome — for model calibration tracking."""

    __tablename__ = "fin_prediction_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("fin_ml_models.id"))
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("fin_alpha_signals.id"))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("fin_assets.id"))

    predicted_direction: Mapped[str | None] = mapped_column(String(10))
    predicted_confidence: Mapped[float | None] = mapped_column(Float)
    actual_outcome: Mapped[str | None] = mapped_column(String(20))
    actual_return_pct: Mapped[float | None] = mapped_column(Float)

    prediction_date: Mapped[str | None] = mapped_column(String(10))
    resolution_date: Mapped[str | None] = mapped_column(String(10))

    __table_args__ = (
        Index("idx_predictions_model", "model_id"),
        Index("idx_predictions_date", "prediction_date"),
    )
