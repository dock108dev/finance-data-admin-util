# Sports → Financial Concept Mapping

Complete mapping between sports-data-admin and fin-data-admin concepts.

## Entity Mapping

| Sports Entity | Financial Entity | Table |
|---------------|-----------------|-------|
| `sports_leagues` (NBA, NHL, NCAAB) | `fin_asset_classes` (STOCKS, CRYPTO) | Asset classes |
| `sports_teams` | `fin_assets` | Individual tickers |
| `sports_games` | `fin_sessions` | Trading sessions |
| `sports_game_plays` | `fin_candles` | OHLCV time series |
| `sports_team_boxscores` | `fin_session_summaries` | Session stats |
| `sports_player_boxscores` | `fin_asset_fundamentals` | Fundamental data |
| `sports_game_odds` | `fin_exchange_prices` | Exchange price history |
| `fairbet_game_odds_work` | `fin_arbitrage_work` | Real-time comparison |
| `sports_game_stories` | `fin_market_analyses` | AI narratives |
| `sports_game_timeline_artifacts` | `fin_session_timelines` | Merged timelines |
| `team_social_posts` | `fin_social_posts` | Social posts |
| `team_social_accounts` | `fin_social_accounts` | Tracked accounts |
| `sports_scrape_runs` | `fin_scrape_runs` | Run tracking |
| `sports_job_runs` | `fin_job_runs` | Job tracking |
| `sports_game_conflicts` | `fin_data_conflicts` | Data conflicts |

## Concept Mapping

| Sports Concept | Financial Concept |
|----------------|-------------------|
| League (NBA) | Asset class (STOCKS) |
| Team (Lakers) | Asset (AAPL) |
| Game (LAL vs BOS) | Trading session (AAPL 2024-01-15) |
| Play-by-play | OHLCV candles (1m, 5m, 1h, 1d) |
| Boxscore | Session summary (OHLCV, volume, indicators) |
| Player stats | Fundamental data (P/E, EPS, TVL) |
| Sportsbook (DraftKings) | Exchange (Binance, Coinbase) |
| Odds (spread, total, ML) | Price (spot, bid, ask) |
| FairBet work table | Arbitrage work table |
| +EV (positive expected value) | Alpha signal (cross-exchange arb) |
| Pinnacle (sharp book) | Binance / NYSE (reference exchange) |
| Vig removal (devig) | Fee estimation |
| Closing line value (CLV) | Execution price vs. signal price |
| Game status (scheduled→live→final) | Session status (scheduled→live→closed) |
| Game flow narrative | Market analysis narrative |
| Drama analysis | Volatility profile |
| Social (team tweets) | Social (cashtag mentions, Reddit) |
| Season | Year / Quarter |

## Pipeline Mapping

| Sports Pipeline | Financial Pipeline |
|-----------------|-------------------|
| Daily sports ingestion | Daily price ingestion |
| Live PBP polling | Intraday price polling |
| Mainline odds sync | Exchange price sync |
| Prop odds sync | (not applicable) |
| Social collection | Social sentiment collection |
| Game flow generation | Market analysis generation |
| Daily sweep | Daily sweep |
| Game state updater | Session state updater |

## Admin UI Mapping

| Sports Admin Page | Financial Admin Page |
|-------------------|---------------------|
| Game Browser | Market Browser |
| Team List | Asset List |
| Game Detail | Session Detail |
| FairBet Odds Viewer | Signal Viewer |
| Control Panel | Control Panel |
| Runs Drawer | Runs Panel |
| (none) | Portfolio Tracker |

## Signal / EV Mapping

| Sports EV Concept | Financial Signal Concept |
|-------------------|-------------------------|
| +EV bet | Alpha signal |
| EV % | Estimated profit % |
| Pinnacle devig | Reference exchange price |
| Confidence tier (HIGH/MED/LOW) | Confidence tier (HIGH/MED/LOW) |
| ev_disabled_reason | disabled_reason |
| Book exclusion (offshore) | Exchange exclusion (unverified) |
| Market category (mainline, prop) | Market type (spot, futures) |
| Logit-space extrapolation | (not applicable) |
