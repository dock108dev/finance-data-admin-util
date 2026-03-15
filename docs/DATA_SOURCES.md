# Data Sources

## Stock Data

### Yahoo Finance (yfinance)
- **Data**: OHLCV, fundamentals, dividends, splits
- **Rate limit**: Informal, ~2000 req/hr
- **Auth**: None required
- **Used for**: Daily + intraday candles, fundamentals

### Alpha Vantage
- **Data**: Intraday, technicals, earnings calendar
- **Rate limit**: 5 req/min (free), 75 req/min (premium)
- **Auth**: API key
- **Used for**: Backup intraday source, earnings data

### Polygon.io
- **Data**: Real-time ticks, aggregates, news, reference data
- **Rate limit**: Varies by plan
- **Auth**: API key
- **Used for**: Tick data, news feed, reference data

### SEC EDGAR
- **Data**: 10-K, 10-Q, 8-K filings
- **Rate limit**: 10 req/sec
- **Auth**: User-Agent header
- **Used for**: Fundamental analysis, filing alerts

## Crypto Data

### Binance API
- **Data**: Spot prices, klines, order book, trades
- **Rate limit**: 1200 req/min
- **Auth**: API key + secret (for authenticated endpoints)
- **Used for**: Primary price source, exchange sync reference

### CoinGecko
- **Data**: Market data, volume, market cap, historical
- **Rate limit**: 30 req/min (free), 500 req/min (pro)
- **Auth**: API key (pro)
- **Used for**: Daily candles, fundamentals, market cap data

### CoinMarketCap
- **Data**: Rankings, metadata, global metrics
- **Rate limit**: 333 req/day (free)
- **Auth**: API key
- **Used for**: Asset metadata, ranking data

### Etherscan
- **Data**: Transactions, token transfers, gas prices
- **Rate limit**: 5 req/sec
- **Auth**: API key
- **Used for**: Whale tracking, on-chain metrics

## Social & Sentiment

### Twitter/X
- **Data**: Cashtag mentions, influencer posts
- **Method**: Playwright scraping (advanced search)
- **Auth**: Auth token + CSRF token
- **Used for**: Social sentiment, influencer tracking

### Reddit (PRAW)
- **Data**: r/wallstreetbets, r/cryptocurrency, r/stocks
- **Rate limit**: 60 req/min
- **Auth**: Client ID + secret
- **Used for**: Retail sentiment, trending tickers

### NewsAPI
- **Data**: News articles from 150k+ sources
- **Rate limit**: 100 req/day (free)
- **Auth**: API key
- **Used for**: News sentiment, event detection

### Fear & Greed Index
- **Data**: Market sentiment index (0-100)
- **Source**: alternative.me (crypto), CNN (stocks)
- **Rate limit**: None
- **Used for**: Market-wide sentiment baseline

## Ingestion Schedule

| Source | Cadence | Asset Class | Quiet Window |
|--------|---------|-------------|--------------|
| yfinance (daily) | Daily 5:00 UTC | STOCKS | N/A |
| yfinance (intraday) | Every 5 min | STOCKS | Non-market hours |
| Binance (sync) | Every 1 min | CRYPTO | Never |
| CoinGecko (daily) | Daily 5:00 UTC | CRYPTO | N/A |
| Exchange sync (arb) | Every 1 min | CRYPTO | Never |
| Social scrape | Every 30 min | ALL | 3-7 AM ET |
| News | Every 30 min | ALL | Never |
| On-chain | Every 15 min | CRYPTO | Never |
| Fundamentals | Daily 6:00 UTC | ALL | N/A |
