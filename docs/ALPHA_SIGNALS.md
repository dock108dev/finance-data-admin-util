# Alpha Signals — Edge Detection Framework

Equivalent to sports-data-admin's FairBet / +EV system.

## Overview

The alpha signal framework detects actionable opportunities across
stocks and crypto using multiple signal types, each with confidence
tiers and strategy configurations.

## Signal Types

| Signal Type | Description | Equivalent |
|-------------|-------------|------------|
| `CROSS_EXCHANGE_ARB` | Price discrepancy across exchanges | Cross-book odds comparison |
| `TECHNICAL_BREAKOUT` | RSI + MACD + BB convergence | N/A (new) |
| `SENTIMENT_DIVERGENCE` | Social sentiment vs. price mismatch | N/A (new) |
| `WHALE_ACCUMULATION` | On-chain whale buying detection | N/A (crypto only) |
| `VOLUME_ANOMALY` | Unusual volume spike | N/A (new) |
| `MOMENTUM_SHIFT` | Trend reversal indicators | N/A (new) |
| `FUNDAMENTAL_MISPRICING` | Price vs. fundamentals divergence | N/A (new) |

## Cross-Exchange Arbitrage (Primary — equiv. to +EV)

### How It Works

1. **Reference Exchange**: Use Binance (crypto) or NYSE (stocks) as the
   "sharp" reference — equivalent to Pinnacle in sports betting
2. **Fetch prices from all exchanges**: Binance, Coinbase, Kraken, etc.
3. **Compute spread %**: `(exchange_price - reference_price) / reference_price`
4. **Subtract fees**: Estimated round-trip trading fees
5. **Flag actionable**: If net profit after fees > 0

### Example

```
Reference: Binance BTC = $65,000
Coinbase:  BTC = $65,350  (+0.54%)  → After 0.2% fees = +0.34% profit
Kraken:    BTC = $65,100  (+0.15%)  → After 0.3% fees = -0.15% (not actionable)
```

### Eligibility Checks (equiv. to EV Eligibility)

| Check | Description | Disabled Reason |
|-------|-------------|-----------------|
| Strategy exists | Valid (asset_class, market_type) combo | `no_strategy` |
| Reference present | Reference exchange has data | `reference_missing` |
| Data freshness | Reference data < max staleness | `reference_stale` |
| Min exchanges | >= N qualifying exchanges | `insufficient_exchanges` |

### Confidence Tiers

| Tier | Criteria | Example |
|------|----------|---------|
| HIGH | Spread > 2%, high liquidity, tight reference | BTC/ETH spot, large-cap stocks |
| MEDIUM | Spread 1-2%, moderate liquidity | Mid-cap alts, mid-cap stocks |
| LOW | Spread < 1%, thin liquidity | Small-cap tokens |

### Strategy Configurations

```python
CRYPTO_SPOT_LARGE_CAP:
    reference: Binance
    min_exchanges: 4
    max_staleness: 60s
    min_spread: 0.3%
    fee_estimate: 0.2%

STOCK_LARGE_CAP:
    reference: NYSE
    min_exchanges: 2
    max_staleness: 300s
    min_spread: 0.05%
    fee_estimate: 0.02%
```

## Technical Signals

### RSI (Relative Strength Index)
- **Buy signal**: RSI < 30 (oversold)
- **Sell signal**: RSI > 70 (overbought)
- **Strength**: Distance from 30/70 threshold

### MACD (Moving Average Convergence Divergence)
- **Buy signal**: Histogram crosses above zero
- **Sell signal**: Histogram crosses below zero
- **Strength**: Magnitude of histogram relative to signal line

### Bollinger Bands
- **Buy signal**: Price below lower band
- **Sell signal**: Price above upper band
- **Strength**: Distance from band boundary

## Sentiment Divergence

Detects when social sentiment disagrees with price action:

- **Bullish divergence**: Price dropping, sentiment bullish → potential bounce
- **Bearish divergence**: Price rising, sentiment bearish → potential drop
- **Threshold**: |divergence| > 0.3 to flag

## Signal Lifecycle

```
DETECTED → PENDING → { HIT | MISS | EXPIRED }
```

1. Signal detected with entry, target, stop-loss
2. Tracked until resolved:
   - **HIT**: Target price reached
   - **MISS**: Stop-loss triggered
   - **EXPIRED**: Neither within expiry window
3. `actual_return_pct` computed on resolution
