# Market Analysis Pipeline

Equivalent to sports-data-admin's 8-stage game flow pipeline.

## Pipeline Stages

```
1. COLLECT_CANDLES
   ↓  Fetch + normalize OHLCV data for the session
2. COMPUTE_INDICATORS
   ↓  Calculate RSI, MACD, BB, VWAP
3. VALIDATE_DATA
   ↓  Check for gaps, outliers, stale data
4. DETECT_EVENTS
   ↓  Identify key price/volume events
5. ANALYZE_SENTIMENT
   ↓  Merge social + news sentiment
6. GENERATE_NARRATIVE
   ↓  AI-powered market narrative (OpenAI GPT-4o)
7. VALIDATE_NARRATIVE
   ↓  Enforce guardrails (block count, word count)
8. FINALIZE
   ↓  Persist to fin_market_analyses + fin_session_timelines
```

## Narrative Semantic Roles

| Role | Description | Equiv. Sports Role |
|------|-------------|--------------------|
| SETUP | Pre-market context, overnight moves | SETUP |
| CATALYST | Event that triggered the main move | MOMENTUM_SHIFT |
| REACTION | Market response to catalyst | RESPONSE |
| DECISION_POINT | Key support/resistance level test | DECISION_POINT |
| RESOLUTION | Session outcome and close | RESOLUTION |

## Guardrails

| Constraint | Limit | Type |
|------------|-------|------|
| Block count | 3-5 | Hard |
| Words per block | 30-120 | Warning |
| Total words | ≤500 | Warning |
| Must have SETUP | First block | Hard |
| Must have RESOLUTION | Last block | Hard |

## Schedule

| Asset Class | Time (UTC) | Time (ET) |
|-------------|-----------|-----------|
| STOCKS | 06:00 | 1:00 AM |
| CRYPTO | 07:00 | 2:00 AM |

## Example Output

```json
{
  "narrative_blocks": [
    {
      "role": "SETUP",
      "content": "BTC opened at $65,200, extending overnight gains..."
    },
    {
      "role": "CATALYST",
      "content": "A whale wallet moved 2,500 BTC off Binance..."
    },
    {
      "role": "REACTION",
      "content": "Volume surged 340% as retail traders piled in..."
    },
    {
      "role": "RESOLUTION",
      "content": "BTC closed at $67,800, marking a 4.0% session gain..."
    }
  ]
}
```
