"""Alpha signal computation engine — equivalent to sports-data-admin's ev.py.

Computes cross-exchange arbitrage, technical breakouts, sentiment divergence,
and other alpha signals. Mirrors the EV computation framework but adapted
for financial markets.

Core functions:
    evaluate_signal_eligibility()  → equiv. evaluate_ev_eligibility()
    compute_arbitrage()            → equiv. compute_ev_for_market()
    compute_technical_signals()    → new (RSI, MACD, BB convergence)
    compute_sentiment_divergence() → new (price vs. sentiment mismatch)
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class ExchangeQuote:
    """A price quote from a specific exchange."""
    exchange: str
    price: float
    bid: float | None = None
    ask: float | None = None
    volume_24h: float | None = None
    observed_at: datetime | None = None


@dataclass
class SignalEligibility:
    """Result of eligibility check — equiv. to EV eligibility."""
    eligible: bool
    reason: str | None = None
    strategy_config: "AlphaStrategyConfig | None" = None


@dataclass
class ArbitrageResult:
    """Cross-exchange arbitrage computation result."""
    reference_exchange: str
    reference_price: float
    opportunities: list["ArbitrageOpportunity"]


@dataclass
class ArbitrageOpportunity:
    """A single arbitrage opportunity on one exchange."""
    exchange: str
    price: float
    spread_pct: float          # % difference from reference
    direction: str             # "BUY" or "SELL" (relative to reference)
    estimated_profit_pct: float
    confidence_tier: str       # "HIGH", "MEDIUM", "LOW"
    is_actionable: bool        # After fees / slippage


@dataclass
class TechnicalSignal:
    """Result of technical indicator analysis."""
    indicator: str             # "RSI", "MACD", "BB", "VWAP"
    value: float
    signal: str                # "BUY", "SELL", "NEUTRAL"
    strength: float            # 0.0 to 1.0


@dataclass
class AlphaStrategyConfig:
    """Configuration for a signal strategy — equiv. to EVStrategyConfig."""
    strategy_name: str
    reference_exchanges: tuple[str, ...]   # "sharp" exchanges with best liquidity
    min_qualifying_exchanges: int
    max_reference_staleness_seconds: int
    confidence_tier: str
    min_spread_threshold: float            # Minimum spread to flag
    fee_estimate_pct: float                # Estimated round-trip fees


# ── Strategy Configurations ──────────────────────────────────────────────────

CRYPTO_ARB_STRATEGY = AlphaStrategyConfig(
    strategy_name="crypto_cross_exchange",
    reference_exchanges=("Binance",),
    min_qualifying_exchanges=3,
    max_reference_staleness_seconds=60,
    confidence_tier="HIGH",
    min_spread_threshold=0.5,    # 0.5% minimum spread
    fee_estimate_pct=0.2,        # 0.2% round-trip fees
)

STOCK_ARB_STRATEGY = AlphaStrategyConfig(
    strategy_name="stock_exchange_comparison",
    reference_exchanges=("NYSE",),
    min_qualifying_exchanges=2,
    max_reference_staleness_seconds=300,
    confidence_tier="MEDIUM",
    min_spread_threshold=0.1,
    fee_estimate_pct=0.05,
)

# Map (asset_class, market_type) → strategy
STRATEGY_MAP: dict[tuple[str, str], AlphaStrategyConfig | None] = {
    ("CRYPTO", "spot"): CRYPTO_ARB_STRATEGY,
    ("CRYPTO", "futures"): None,          # Disabled for now
    ("STOCKS", "spot"): STOCK_ARB_STRATEGY,
    ("STOCKS", "options"): None,          # Disabled for now
}


# ── Excluded / Included Exchanges (equiv. EXCLUDED_BOOKS) ───────────────────

EXCLUDED_EXCHANGES: set[str] = {
    "Unknown DEX",
    "Unverified",
}

INCLUDED_CRYPTO_EXCHANGES: set[str] = {
    "Binance", "Coinbase", "Kraken", "Bybit", "OKX",
    "KuCoin", "Gate.io", "Bitfinex", "Gemini", "Bitstamp",
}

INCLUDED_STOCK_EXCHANGES: set[str] = {
    "NYSE", "NASDAQ", "CBOE", "ARCA", "BATS",
}


# ── Core Functions ───────────────────────────────────────────────────────────

def evaluate_signal_eligibility(
    asset_class: str,
    market_type: str,
    quotes: list[ExchangeQuote],
    now: datetime | None = None,
) -> SignalEligibility:
    """Four-check eligibility gate — equiv. to evaluate_ev_eligibility().

    Check 1: Strategy exists for (asset_class, market_type)
    Check 2: Reference exchange present
    Check 3: Reference data freshness
    Check 4: Minimum qualifying exchanges
    """
    now = now or datetime.utcnow()

    # Check 1: Strategy exists
    strategy = STRATEGY_MAP.get((asset_class, market_type))
    if strategy is None:
        return SignalEligibility(eligible=False, reason="no_strategy")

    # Check 2: Reference exchange present
    ref_quotes = [q for q in quotes if q.exchange in strategy.reference_exchanges]
    if not ref_quotes:
        return SignalEligibility(eligible=False, reason="reference_missing")

    # Check 3: Freshness
    for rq in ref_quotes:
        if rq.observed_at is None:
            return SignalEligibility(eligible=False, reason="reference_stale")
        age = (now - rq.observed_at).total_seconds()
        if age > strategy.max_reference_staleness_seconds:
            return SignalEligibility(eligible=False, reason="reference_stale")

    # Check 4: Minimum qualifying exchanges
    qualifying = [
        q for q in quotes
        if q.exchange not in EXCLUDED_EXCHANGES
    ]
    if len(qualifying) < strategy.min_qualifying_exchanges:
        return SignalEligibility(eligible=False, reason="insufficient_exchanges")

    return SignalEligibility(eligible=True, strategy_config=strategy)


def compute_arbitrage(
    quotes: list[ExchangeQuote],
    strategy: AlphaStrategyConfig,
) -> ArbitrageResult:
    """Compute cross-exchange arbitrage — equiv. to compute_ev_for_market().

    Steps:
    1. Find reference price (from reference exchange)
    2. Compute spread % for each other exchange
    3. Subtract estimated fees
    4. Flag actionable opportunities
    """
    # Step 1: Reference price
    ref_quote = next(
        q for q in quotes if q.exchange in strategy.reference_exchanges
    )
    ref_price = ref_quote.price

    # Step 2-4: Compute per-exchange
    opportunities: list[ArbitrageOpportunity] = []
    for quote in quotes:
        if quote.exchange in strategy.reference_exchanges:
            continue
        if quote.exchange in EXCLUDED_EXCHANGES:
            continue

        spread_pct = ((quote.price - ref_price) / ref_price) * 100
        direction = "SELL" if spread_pct > 0 else "BUY"
        estimated_profit = abs(spread_pct) - strategy.fee_estimate_pct

        # Confidence based on spread magnitude
        if abs(spread_pct) > 2.0:
            confidence = "HIGH"
        elif abs(spread_pct) > 1.0:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        opportunities.append(ArbitrageOpportunity(
            exchange=quote.exchange,
            price=quote.price,
            spread_pct=round(spread_pct, 4),
            direction=direction,
            estimated_profit_pct=round(max(0, estimated_profit), 4),
            confidence_tier=confidence,
            is_actionable=estimated_profit > 0,
        ))

    return ArbitrageResult(
        reference_exchange=ref_quote.exchange,
        reference_price=ref_price,
        opportunities=sorted(
            opportunities,
            key=lambda o: abs(o.spread_pct),
            reverse=True,
        ),
    )


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """Compute Relative Strength Index."""
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-(period):]

    gains = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def compute_macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[float, float, float] | None:
    """Compute MACD line, signal line, and histogram.

    Returns: (macd_line, signal_line, histogram) or None if insufficient data.
    """
    if len(closes) < slow + signal_period:
        return None

    def ema(data: list[float], period: int) -> list[float]:
        multiplier = 2 / (period + 1)
        result = [data[0]]
        for i in range(1, len(data)):
            result.append(data[i] * multiplier + result[-1] * (1 - multiplier))
        return result

    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)

    macd_line_values = [f - s for f, s in zip(fast_ema, slow_ema)]
    signal_line_values = ema(macd_line_values, signal_period)

    macd_val = macd_line_values[-1]
    signal_val = signal_line_values[-1]
    histogram = macd_val - signal_val

    return (round(macd_val, 4), round(signal_val, 4), round(histogram, 4))


def compute_bollinger_bands(
    closes: list[float],
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[float, float, float] | None:
    """Compute Bollinger Bands (upper, middle, lower).

    Returns: (upper, middle, lower) or None if insufficient data.
    """
    if len(closes) < period:
        return None

    window = closes[-period:]
    middle = sum(window) / period
    variance = sum((x - middle) ** 2 for x in window) / period
    std = math.sqrt(variance)

    upper = middle + num_std * std
    lower = middle - num_std * std

    return (round(upper, 4), round(middle, 4), round(lower, 4))


def compute_technical_signals(
    closes: list[float],
    current_price: float,
) -> list[TechnicalSignal]:
    """Run all technical indicators and return consolidated signals."""
    signals: list[TechnicalSignal] = []

    # RSI
    rsi = compute_rsi(closes)
    if rsi is not None:
        if rsi < 30:
            signal = "BUY"
            strength = (30 - rsi) / 30
        elif rsi > 70:
            signal = "SELL"
            strength = (rsi - 70) / 30
        else:
            signal = "NEUTRAL"
            strength = 0.0
        signals.append(TechnicalSignal("RSI", rsi, signal, min(strength, 1.0)))

    # MACD
    macd_result = compute_macd(closes)
    if macd_result is not None:
        macd_line, signal_line, histogram = macd_result
        if histogram > 0:
            signal = "BUY"
            strength = min(abs(histogram) / abs(signal_line) if signal_line else 0, 1.0)
        elif histogram < 0:
            signal = "SELL"
            strength = min(abs(histogram) / abs(signal_line) if signal_line else 0, 1.0)
        else:
            signal = "NEUTRAL"
            strength = 0.0
        signals.append(TechnicalSignal("MACD", histogram, signal, strength))

    # Bollinger Bands
    bb = compute_bollinger_bands(closes)
    if bb is not None:
        upper, middle, lower = bb
        if current_price < lower:
            signal = "BUY"
            strength = min((lower - current_price) / (upper - lower), 1.0)
        elif current_price > upper:
            signal = "SELL"
            strength = min((current_price - upper) / (upper - lower), 1.0)
        else:
            signal = "NEUTRAL"
            strength = 0.0
        signals.append(TechnicalSignal("BB", current_price, signal, strength))

    return signals


def compute_sentiment_divergence(
    price_change_pct: float,
    sentiment_score: float,
    threshold: float = 0.3,
) -> TechnicalSignal | None:
    """Detect divergence between price action and social sentiment.

    If price is dropping but sentiment is bullish (or vice versa),
    flag a potential reversal signal.
    """
    # Normalize price change to -1..+1 range (cap at ±10%)
    price_signal = max(-1.0, min(1.0, price_change_pct / 10.0))

    divergence = sentiment_score - price_signal

    if abs(divergence) < threshold:
        return None

    if divergence > 0:
        # Sentiment more bullish than price → potential bounce
        signal = "BUY"
    else:
        # Sentiment more bearish than price → potential drop
        signal = "SELL"

    return TechnicalSignal(
        indicator="SENTIMENT_DIVERGENCE",
        value=round(divergence, 4),
        signal=signal,
        strength=min(abs(divergence), 1.0),
    )
