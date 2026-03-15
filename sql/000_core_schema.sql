-- =============================================================================
-- Fin Data Admin — Core Schema
-- =============================================================================
-- Equivalent to sports-data-admin's 000_sports_schema.sql
-- Run against a fresh PostgreSQL 15+ database.

-- ── Asset Classes (equiv. sports_leagues) ───────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_asset_classes (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20) UNIQUE NOT NULL,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO fin_asset_classes (code, name, description) VALUES
    ('STOCKS', 'US Equities', 'NYSE and NASDAQ listed stocks'),
    ('CRYPTO', 'Cryptocurrency', 'Digital assets and tokens')
ON CONFLICT (code) DO NOTHING;


-- ── Assets (equiv. sports_teams) ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_assets (
    id                  SERIAL PRIMARY KEY,
    asset_class_id      INTEGER NOT NULL REFERENCES fin_asset_classes(id),
    ticker              VARCHAR(20) NOT NULL,
    name                VARCHAR(200) NOT NULL,
    description         TEXT,
    sector              VARCHAR(100),
    industry            VARCHAR(100),
    market_cap          DOUBLE PRECISION,
    exchange            VARCHAR(50),
    is_active           BOOLEAN DEFAULT TRUE,
    external_ids        JSONB,
    twitter_handle      VARCHAR(100),
    subreddit           VARCHAR(100),
    logo_url            VARCHAR(500),
    color_hex           VARCHAR(7),
    last_price_at       TIMESTAMPTZ,
    last_fundamental_at TIMESTAMPTZ,
    last_social_at      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (asset_class_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_assets_ticker ON fin_assets(ticker);
CREATE INDEX IF NOT EXISTS idx_assets_class_active ON fin_assets(asset_class_id, is_active);


-- ── Market Sessions (equiv. sports_games) ───────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_sessions (
    id              SERIAL PRIMARY KEY,
    asset_id        INTEGER NOT NULL REFERENCES fin_assets(id),
    asset_class_id  INTEGER NOT NULL REFERENCES fin_asset_classes(id),
    session_date    DATE NOT NULL,
    open_time       TIMESTAMPTZ,
    close_time      TIMESTAMPTZ,
    open_price      DOUBLE PRECISION,
    high_price      DOUBLE PRECISION,
    low_price       DOUBLE PRECISION,
    close_price     DOUBLE PRECISION,
    volume          DOUBLE PRECISION,
    vwap            DOUBLE PRECISION,
    change_pct      DOUBLE PRECISION,
    range_pct       DOUBLE PRECISION,
    dollar_volume   DOUBLE PRECISION,
    status          VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    raw_data        JSONB,
    last_scraped_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (asset_id, session_date)
);

CREATE INDEX IF NOT EXISTS idx_sessions_class_date ON fin_sessions(asset_class_id, session_date);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON fin_sessions(status);


-- ── Candles (equiv. sports_game_plays) ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_candles (
    id          BIGSERIAL PRIMARY KEY,
    asset_id    INTEGER NOT NULL REFERENCES fin_assets(id),
    session_id  INTEGER REFERENCES fin_sessions(id),
    timestamp   TIMESTAMPTZ NOT NULL,
    interval    VARCHAR(10) NOT NULL,
    open        DOUBLE PRECISION NOT NULL,
    high        DOUBLE PRECISION NOT NULL,
    low         DOUBLE PRECISION NOT NULL,
    close       DOUBLE PRECISION NOT NULL,
    volume      DOUBLE PRECISION NOT NULL,
    vwap        DOUBLE PRECISION,
    trade_count INTEGER,
    source      VARCHAR(50) NOT NULL,
    raw_payload JSONB,
    UNIQUE (asset_id, interval, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_candles_asset_time ON fin_candles(asset_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_candles_interval ON fin_candles(interval);


-- ── Session Summaries (equiv. sports_team_boxscores) ────────────────────────

CREATE TABLE IF NOT EXISTS fin_session_summaries (
    id              SERIAL PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES fin_sessions(id),
    asset_id        INTEGER NOT NULL REFERENCES fin_assets(id),
    total_volume    DOUBLE PRECISION,
    total_trades    INTEGER,
    avg_spread      DOUBLE PRECISION,
    volatility      DOUBLE PRECISION,
    max_drawdown    DOUBLE PRECISION,
    rsi_14          DOUBLE PRECISION,
    macd_signal     DOUBLE PRECISION,
    bb_upper        DOUBLE PRECISION,
    bb_lower        DOUBLE PRECISION,
    raw_stats_json  JSONB,
    source          VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, asset_id)
);


-- ── Asset Fundamentals (equiv. sports_player_boxscores) ─────────────────────

CREATE TABLE IF NOT EXISTS fin_asset_fundamentals (
    id                      SERIAL PRIMARY KEY,
    asset_id                INTEGER NOT NULL REFERENCES fin_assets(id),
    snapshot_date           DATE NOT NULL,
    pe_ratio                DOUBLE PRECISION,
    eps                     DOUBLE PRECISION,
    dividend_yield          DOUBLE PRECISION,
    revenue                 DOUBLE PRECISION,
    profit_margin           DOUBLE PRECISION,
    tvl                     DOUBLE PRECISION,
    circulating_supply      DOUBLE PRECISION,
    max_supply              DOUBLE PRECISION,
    active_addresses_24h    INTEGER,
    txn_volume_24h          DOUBLE PRECISION,
    market_cap              DOUBLE PRECISION,
    fully_diluted_valuation DOUBLE PRECISION,
    raw_data                JSONB,
    source                  VARCHAR(50),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (asset_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_fundamentals_asset ON fin_asset_fundamentals(asset_id);


-- ── Exchange Prices (equiv. sports_game_odds) ───────────────────────────────

CREATE TABLE IF NOT EXISTS fin_exchange_prices (
    id          SERIAL PRIMARY KEY,
    asset_id    INTEGER NOT NULL REFERENCES fin_assets(id),
    exchange    VARCHAR(50) NOT NULL,
    price_type  VARCHAR(20) NOT NULL,
    price       DOUBLE PRECISION NOT NULL,
    volume_24h  DOUBLE PRECISION,
    bid         DOUBLE PRECISION,
    ask         DOUBLE PRECISION,
    spread      DOUBLE PRECISION,
    spread_pct  DOUBLE PRECISION,
    observed_at TIMESTAMPTZ NOT NULL,
    is_closing  BOOLEAN DEFAULT FALSE,
    raw_payload JSONB,
    UNIQUE (asset_id, exchange, price_type, is_closing)
);

CREATE INDEX IF NOT EXISTS idx_exchange_prices_asset ON fin_exchange_prices(asset_id);
CREATE INDEX IF NOT EXISTS idx_exchange_prices_observed ON fin_exchange_prices(observed_at);
CREATE INDEX IF NOT EXISTS idx_exchange_prices_exchange ON fin_exchange_prices(exchange);


-- ── Arbitrage Work Table (equiv. fairbet_game_odds_work) ────────────────────

CREATE TABLE IF NOT EXISTS fin_arbitrage_work (
    asset_id            INTEGER NOT NULL REFERENCES fin_assets(id),
    pair_key            VARCHAR(100) NOT NULL,
    exchange            VARCHAR(50) NOT NULL,
    price               DOUBLE PRECISION NOT NULL,
    bid                 DOUBLE PRECISION,
    ask                 DOUBLE PRECISION,
    volume_24h          DOUBLE PRECISION,
    spread_vs_reference DOUBLE PRECISION,
    arb_pct             DOUBLE PRECISION,
    reference_exchange  VARCHAR(50),
    observed_at         TIMESTAMPTZ NOT NULL,
    market_category     VARCHAR(50),
    PRIMARY KEY (asset_id, pair_key, exchange)
);

CREATE INDEX IF NOT EXISTS idx_arb_work_asset ON fin_arbitrage_work(asset_id);
CREATE INDEX IF NOT EXISTS idx_arb_work_observed ON fin_arbitrage_work(observed_at);


-- ── Alpha Signals (equiv. +EV tracking) ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_alpha_signals (
    id                  SERIAL PRIMARY KEY,
    asset_id            INTEGER NOT NULL REFERENCES fin_assets(id),
    asset_class_id      INTEGER NOT NULL REFERENCES fin_asset_classes(id),
    signal_type         VARCHAR(50) NOT NULL,
    signal_subtype      VARCHAR(50),
    direction           VARCHAR(10) NOT NULL,
    strength            DOUBLE PRECISION NOT NULL,
    confidence_tier     VARCHAR(10) NOT NULL,
    ev_estimate         DOUBLE PRECISION,
    trigger_price       DOUBLE PRECISION,
    target_price        DOUBLE PRECISION,
    stop_loss           DOUBLE PRECISION,
    risk_reward_ratio   DOUBLE PRECISION,
    detected_at         TIMESTAMPTZ NOT NULL,
    expires_at          TIMESTAMPTZ,
    resolved_at         TIMESTAMPTZ,
    outcome             VARCHAR(20),
    actual_return_pct   DOUBLE PRECISION,
    disabled_reason     VARCHAR(100),
    derivation          JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_asset_type ON fin_alpha_signals(asset_id, signal_type);
CREATE INDEX IF NOT EXISTS idx_signals_detected ON fin_alpha_signals(detected_at);
CREATE INDEX IF NOT EXISTS idx_signals_confidence ON fin_alpha_signals(confidence_tier);
CREATE INDEX IF NOT EXISTS idx_signals_outcome ON fin_alpha_signals(outcome);


-- ── Market Analysis (equiv. sports_game_stories) ────────────────────────────

CREATE TABLE IF NOT EXISTS fin_market_analyses (
    id                      SERIAL PRIMARY KEY,
    asset_id                INTEGER NOT NULL REFERENCES fin_assets(id),
    session_id              INTEGER REFERENCES fin_sessions(id),
    analysis_date           DATE NOT NULL,
    key_moments_json        JSONB,
    narrative_blocks_json   JSONB,
    summary                 TEXT,
    analysis_version        INTEGER DEFAULT 1,
    generated_by            VARCHAR(50),
    generated_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (asset_id, analysis_date, analysis_version)
);


-- ── Session Timelines (equiv. sports_game_timeline_artifacts) ───────────────

CREATE TABLE IF NOT EXISTS fin_session_timelines (
    id                      SERIAL PRIMARY KEY,
    session_id              INTEGER NOT NULL REFERENCES fin_sessions(id),
    asset_id                INTEGER NOT NULL REFERENCES fin_assets(id),
    timeline_json           JSONB,
    market_analysis_json    JSONB,
    summary_json            JSONB,
    timeline_version        INTEGER DEFAULT 1,
    generated_at            TIMESTAMPTZ,
    generated_by            VARCHAR(50),
    generation_reason       VARCHAR(100),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, asset_id, timeline_version)
);


-- ── Social Posts (equiv. team_social_posts) ─────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_social_posts (
    id                  SERIAL PRIMARY KEY,
    asset_id            INTEGER REFERENCES fin_assets(id),
    session_id          INTEGER REFERENCES fin_sessions(id),
    platform            VARCHAR(20) NOT NULL,
    external_post_id    VARCHAR(100) NOT NULL,
    post_url            VARCHAR(500),
    author              VARCHAR(200),
    author_followers    INTEGER,
    text                TEXT,
    has_media           BOOLEAN DEFAULT FALSE,
    media_url           VARCHAR(500),
    likes_count         INTEGER,
    retweets_count      INTEGER,
    replies_count       INTEGER,
    score               INTEGER,
    sentiment_score     DOUBLE PRECISION,
    sentiment_label     VARCHAR(20),
    mapping_status      VARCHAR(20) DEFAULT 'unmapped',
    cashtags            JSONB,
    posted_at           TIMESTAMPTZ NOT NULL,
    is_influencer       BOOLEAN DEFAULT FALSE,
    influence_tier      VARCHAR(10),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (platform, external_post_id)
);

CREATE INDEX IF NOT EXISTS idx_social_posts_asset ON fin_social_posts(asset_id);
CREATE INDEX IF NOT EXISTS idx_social_posts_posted ON fin_social_posts(posted_at);
CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON fin_social_posts(platform);
CREATE INDEX IF NOT EXISTS idx_social_posts_mapping ON fin_social_posts(mapping_status);


-- ── Social Accounts (equiv. team_social_accounts) ──────────────────────────

CREATE TABLE IF NOT EXISTS fin_social_accounts (
    id                  SERIAL PRIMARY KEY,
    asset_id            INTEGER REFERENCES fin_assets(id),
    platform            VARCHAR(20) NOT NULL,
    handle              VARCHAR(200) NOT NULL,
    account_type        VARCHAR(30) NOT NULL,
    followers           INTEGER,
    verified            BOOLEAN DEFAULT FALSE,
    last_collected_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (platform, handle)
);


-- ── Sentiment Snapshots ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_sentiment_snapshots (
    id                  SERIAL PRIMARY KEY,
    asset_id            INTEGER REFERENCES fin_assets(id),
    asset_class_id      INTEGER REFERENCES fin_asset_classes(id),
    fear_greed_index    INTEGER,
    social_volume       INTEGER,
    bullish_pct         DOUBLE PRECISION,
    bearish_pct         DOUBLE PRECISION,
    neutral_pct         DOUBLE PRECISION,
    weighted_sentiment  DOUBLE PRECISION,
    twitter_sentiment   DOUBLE PRECISION,
    reddit_sentiment    DOUBLE PRECISION,
    news_sentiment      DOUBLE PRECISION,
    observed_at         TIMESTAMPTZ NOT NULL,
    window_minutes      INTEGER DEFAULT 60,
    raw_data            JSONB,
    source              VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_sentiment_asset_time ON fin_sentiment_snapshots(asset_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_sentiment_class_time ON fin_sentiment_snapshots(asset_class_id, observed_at);


-- ── News Articles ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_news_articles (
    id                  SERIAL PRIMARY KEY,
    asset_id            INTEGER REFERENCES fin_assets(id),
    title               VARCHAR(500) NOT NULL,
    url                 VARCHAR(1000) NOT NULL UNIQUE,
    source              VARCHAR(100) NOT NULL,
    author              VARCHAR(200),
    published_at        TIMESTAMPTZ NOT NULL,
    description         TEXT,
    sentiment_score     DOUBLE PRECISION,
    sentiment_label     VARCHAR(20),
    category            VARCHAR(50),
    tickers_mentioned   JSONB,
    raw_payload         JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_asset ON fin_news_articles(asset_id);
CREATE INDEX IF NOT EXISTS idx_news_published ON fin_news_articles(published_at);


-- ── On-Chain: Whale Wallets ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_whale_wallets (
    id              SERIAL PRIMARY KEY,
    address         VARCHAR(100) UNIQUE NOT NULL,
    chain           VARCHAR(20) NOT NULL,
    label           VARCHAR(200),
    wallet_type     VARCHAR(50),
    balance_usd     DOUBLE PRECISION,
    last_active_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whale_wallets_chain ON fin_whale_wallets(chain);


-- ── On-Chain: Whale Transactions ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_whale_transactions (
    id              SERIAL PRIMARY KEY,
    wallet_id       INTEGER REFERENCES fin_whale_wallets(id),
    asset_id        INTEGER REFERENCES fin_assets(id),
    tx_hash         VARCHAR(200) UNIQUE NOT NULL,
    chain           VARCHAR(20) NOT NULL,
    from_address    VARCHAR(100) NOT NULL,
    to_address      VARCHAR(100) NOT NULL,
    amount          DOUBLE PRECISION NOT NULL,
    amount_usd      DOUBLE PRECISION,
    token_symbol    VARCHAR(20),
    tx_type         VARCHAR(50),
    direction       VARCHAR(20),
    block_number    INTEGER,
    timestamp       TIMESTAMPTZ NOT NULL,
    raw_payload     JSONB
);

CREATE INDEX IF NOT EXISTS idx_whale_tx_asset ON fin_whale_transactions(asset_id);
CREATE INDEX IF NOT EXISTS idx_whale_tx_timestamp ON fin_whale_transactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_whale_tx_type ON fin_whale_transactions(tx_type);


-- ── On-Chain: Metrics ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_onchain_metrics (
    id                  SERIAL PRIMARY KEY,
    asset_id            INTEGER NOT NULL REFERENCES fin_assets(id),
    chain               VARCHAR(20) NOT NULL,
    active_addresses    INTEGER,
    transaction_count   INTEGER,
    avg_gas_price       DOUBLE PRECISION,
    total_fees_usd      DOUBLE PRECISION,
    dex_volume_usd      DOUBLE PRECISION,
    tvl_usd             DOUBLE PRECISION,
    net_exchange_flow    DOUBLE PRECISION,
    observed_at         TIMESTAMPTZ NOT NULL,
    window_hours        INTEGER DEFAULT 24,
    raw_data            JSONB,
    source              VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_onchain_asset_time ON fin_onchain_metrics(asset_id, observed_at);


-- ── Scrape Runs (equiv. sports_scrape_runs) ─────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_scrape_runs (
    id                  SERIAL PRIMARY KEY,
    scraper_type        VARCHAR(50) NOT NULL,
    asset_class_id      INTEGER REFERENCES fin_asset_classes(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    job_id              VARCHAR(100),
    requested_by        VARCHAR(50),
    config              JSONB,
    summary             TEXT,
    error_details       TEXT,
    assets_processed    INTEGER,
    records_created     INTEGER,
    records_updated     INTEGER,
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_scrape_runs_type ON fin_scrape_runs(scraper_type);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_status ON fin_scrape_runs(status);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_started ON fin_scrape_runs(started_at);


-- ── Job Runs (equiv. sports_job_runs) ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_job_runs (
    id                  SERIAL PRIMARY KEY,
    phase               VARCHAR(100) NOT NULL,
    asset_classes       JSONB,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    duration_seconds    DOUBLE PRECISION,
    error_summary       TEXT,
    summary_data        JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_runs_phase ON fin_job_runs(phase);
CREATE INDEX IF NOT EXISTS idx_job_runs_started ON fin_job_runs(started_at);


-- ── Data Conflicts (equiv. sports_game_conflicts) ──────────────────────────

CREATE TABLE IF NOT EXISTS fin_data_conflicts (
    id                  SERIAL PRIMARY KEY,
    asset_class_id      INTEGER REFERENCES fin_asset_classes(id),
    asset_id            INTEGER REFERENCES fin_assets(id),
    conflict_type       VARCHAR(50) NOT NULL,
    source              VARCHAR(50),
    conflict_fields     JSONB,
    description         TEXT,
    resolved_at         TIMESTAMPTZ,
    resolution_notes    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conflicts_type ON fin_data_conflicts(conflict_type);
CREATE INDEX IF NOT EXISTS idx_conflicts_unresolved ON fin_data_conflicts(resolved_at);


-- ── Seed Data: Example Assets ───────────────────────────────────────────────

INSERT INTO fin_assets (asset_class_id, ticker, name, sector, industry, exchange) VALUES
    -- ── Stocks: Mega-cap Tech ──────────────────────────────────────────────────
    (1, 'AAPL',  'Apple Inc.',                   'Technology',       'Consumer Electronics',    'NASDAQ'),
    (1, 'MSFT',  'Microsoft Corp.',              'Technology',       'Software',                'NASDAQ'),
    (1, 'GOOGL', 'Alphabet Inc. Class A',        'Technology',       'Internet Services',       'NASDAQ'),
    (1, 'GOOG',  'Alphabet Inc. Class C',        'Technology',       'Internet Services',       'NASDAQ'),
    (1, 'AMZN',  'Amazon.com Inc.',              'Consumer Cyclical','E-Commerce',              'NASDAQ'),
    (1, 'META',  'Meta Platforms Inc.',           'Technology',       'Internet Services',       'NASDAQ'),
    (1, 'NVDA',  'NVIDIA Corp.',                 'Technology',       'Semiconductors',          'NASDAQ'),
    (1, 'TSLA',  'Tesla Inc.',                   'Consumer Cyclical','Auto Manufacturers',      'NASDAQ'),
    (1, 'AVGO',  'Broadcom Inc.',                'Technology',       'Semiconductors',          'NASDAQ'),
    (1, 'ORCL',  'Oracle Corp.',                 'Technology',       'Software',                'NYSE'),
    (1, 'CRM',   'Salesforce Inc.',              'Technology',       'Software',                'NYSE'),
    (1, 'ADBE',  'Adobe Inc.',                   'Technology',       'Software',                'NASDAQ'),
    (1, 'AMD',   'Advanced Micro Devices Inc.',  'Technology',       'Semiconductors',          'NASDAQ'),
    (1, 'INTC',  'Intel Corp.',                  'Technology',       'Semiconductors',          'NASDAQ'),
    (1, 'CSCO',  'Cisco Systems Inc.',           'Technology',       'Networking',              'NASDAQ'),
    (1, 'IBM',   'International Business Machines','Technology',     'IT Services',             'NYSE'),
    (1, 'QCOM',  'Qualcomm Inc.',                'Technology',       'Semiconductors',          'NASDAQ'),
    (1, 'TXN',   'Texas Instruments Inc.',       'Technology',       'Semiconductors',          'NASDAQ'),
    (1, 'NOW',   'ServiceNow Inc.',              'Technology',       'Software',                'NYSE'),
    (1, 'SHOP',  'Shopify Inc.',                 'Technology',       'E-Commerce',              'NYSE'),
    (1, 'SQ',    'Block Inc.',                   'Technology',       'Fintech',                 'NYSE'),
    (1, 'SNOW',  'Snowflake Inc.',               'Technology',       'Cloud Computing',         'NYSE'),
    (1, 'PLTR',  'Palantir Technologies Inc.',   'Technology',       'Software',                'NYSE'),
    (1, 'NET',   'Cloudflare Inc.',              'Technology',       'Cloud Computing',         'NYSE'),
    (1, 'DDOG',  'Datadog Inc.',                 'Technology',       'Software',                'NASDAQ'),
    (1, 'MDB',   'MongoDB Inc.',                 'Technology',       'Software',                'NASDAQ'),
    (1, 'ZS',    'Zscaler Inc.',                 'Technology',       'Cybersecurity',           'NASDAQ'),
    (1, 'CRWD',  'CrowdStrike Holdings Inc.',    'Technology',       'Cybersecurity',           'NASDAQ'),
    (1, 'PANW',  'Palo Alto Networks Inc.',      'Technology',       'Cybersecurity',           'NASDAQ'),
    (1, 'FTNT',  'Fortinet Inc.',                'Technology',       'Cybersecurity',           'NASDAQ'),

    -- ── Stocks: Financials ─────────────────────────────────────────────────────
    (1, 'JPM',   'JPMorgan Chase & Co.',         'Financial',        'Banks',                   'NYSE'),
    (1, 'BAC',   'Bank of America Corp.',        'Financial',        'Banks',                   'NYSE'),
    (1, 'WFC',   'Wells Fargo & Co.',            'Financial',        'Banks',                   'NYSE'),
    (1, 'GS',    'Goldman Sachs Group Inc.',     'Financial',        'Investment Banking',      'NYSE'),
    (1, 'MS',    'Morgan Stanley',               'Financial',        'Investment Banking',      'NYSE'),
    (1, 'C',     'Citigroup Inc.',               'Financial',        'Banks',                   'NYSE'),
    (1, 'BRK.B', 'Berkshire Hathaway Inc.',      'Financial',        'Conglomerates',           'NYSE'),
    (1, 'AXP',   'American Express Co.',         'Financial',        'Credit Services',         'NYSE'),
    (1, 'SCHW',  'Charles Schwab Corp.',         'Financial',        'Brokerage',               'NYSE'),
    (1, 'BLK',   'BlackRock Inc.',               'Financial',        'Asset Management',        'NYSE'),
    (1, 'SPGI',  'S&P Global Inc.',              'Financial',        'Financial Data',          'NYSE'),
    (1, 'CME',   'CME Group Inc.',               'Financial',        'Exchanges',               'NASDAQ'),
    (1, 'ICE',   'Intercontinental Exchange Inc.','Financial',       'Exchanges',               'NYSE'),
    (1, 'COF',   'Capital One Financial Corp.',  'Financial',        'Credit Services',         'NYSE'),
    (1, 'USB',   'U.S. Bancorp',                 'Financial',        'Banks',                   'NYSE'),
    (1, 'PNC',   'PNC Financial Services Group', 'Financial',        'Banks',                   'NYSE'),
    (1, 'TFC',   'Truist Financial Corp.',       'Financial',        'Banks',                   'NYSE'),
    (1, 'V',     'Visa Inc.',                    'Financial',        'Credit Services',         'NYSE'),
    (1, 'MA',    'Mastercard Inc.',              'Financial',        'Credit Services',         'NYSE'),

    -- ── Stocks: Healthcare ─────────────────────────────────────────────────────
    (1, 'UNH',   'UnitedHealth Group Inc.',      'Healthcare',       'Health Insurance',        'NYSE'),
    (1, 'JNJ',   'Johnson & Johnson',            'Healthcare',       'Pharmaceuticals',         'NYSE'),
    (1, 'LLY',   'Eli Lilly & Co.',              'Healthcare',       'Pharmaceuticals',         'NYSE'),
    (1, 'PFE',   'Pfizer Inc.',                  'Healthcare',       'Pharmaceuticals',         'NYSE'),
    (1, 'ABBV',  'AbbVie Inc.',                  'Healthcare',       'Pharmaceuticals',         'NYSE'),
    (1, 'MRK',   'Merck & Co. Inc.',             'Healthcare',       'Pharmaceuticals',         'NYSE'),
    (1, 'TMO',   'Thermo Fisher Scientific Inc.','Healthcare',       'Diagnostics & Research',  'NYSE'),
    (1, 'ABT',   'Abbott Laboratories',          'Healthcare',       'Medical Devices',         'NYSE'),
    (1, 'DHR',   'Danaher Corp.',                'Healthcare',       'Diagnostics & Research',  'NYSE'),
    (1, 'BMY',   'Bristol-Myers Squibb Co.',     'Healthcare',       'Pharmaceuticals',         'NYSE'),
    (1, 'AMGN',  'Amgen Inc.',                   'Healthcare',       'Biotechnology',           'NASDAQ'),
    (1, 'GILD',  'Gilead Sciences Inc.',         'Healthcare',       'Biotechnology',           'NASDAQ'),
    (1, 'ISRG',  'Intuitive Surgical Inc.',      'Healthcare',       'Medical Devices',         'NASDAQ'),
    (1, 'MDT',   'Medtronic PLC',                'Healthcare',       'Medical Devices',         'NYSE'),
    (1, 'SYK',   'Stryker Corp.',                'Healthcare',       'Medical Devices',         'NYSE'),
    (1, 'REGN',  'Regeneron Pharmaceuticals Inc.','Healthcare',      'Biotechnology',           'NASDAQ'),
    (1, 'VRTX',  'Vertex Pharmaceuticals Inc.',  'Healthcare',       'Biotechnology',           'NASDAQ'),
    (1, 'ZTS',   'Zoetis Inc.',                  'Healthcare',       'Veterinary',              'NYSE'),
    (1, 'DXCM',  'DexCom Inc.',                  'Healthcare',       'Medical Devices',         'NASDAQ'),
    (1, 'MRNA',  'Moderna Inc.',                 'Healthcare',       'Biotechnology',           'NASDAQ'),

    -- ── Stocks: Consumer ───────────────────────────────────────────────────────
    (1, 'WMT',   'Walmart Inc.',                 'Consumer Defensive','Discount Stores',        'NYSE'),
    (1, 'PG',    'Procter & Gamble Co.',         'Consumer Defensive','Household Products',     'NYSE'),
    (1, 'KO',    'Coca-Cola Co.',                'Consumer Defensive','Beverages',              'NYSE'),
    (1, 'PEP',   'PepsiCo Inc.',                 'Consumer Defensive','Beverages',              'NASDAQ'),
    (1, 'COST',  'Costco Wholesale Corp.',       'Consumer Defensive','Discount Stores',        'NASDAQ'),
    (1, 'HD',    'Home Depot Inc.',              'Consumer Cyclical', 'Home Improvement',       'NYSE'),
    (1, 'MCD',   'McDonald''s Corp.',            'Consumer Cyclical', 'Restaurants',            'NYSE'),
    (1, 'NKE',   'NIKE Inc.',                    'Consumer Cyclical', 'Footwear & Accessories', 'NYSE'),
    (1, 'SBUX',  'Starbucks Corp.',              'Consumer Cyclical', 'Restaurants',            'NASDAQ'),
    (1, 'TGT',   'Target Corp.',                 'Consumer Defensive','Discount Stores',        'NYSE'),
    (1, 'LOW',   'Lowe''s Companies Inc.',       'Consumer Cyclical', 'Home Improvement',       'NYSE'),
    (1, 'DIS',   'Walt Disney Co.',              'Communication',     'Entertainment',          'NYSE'),
    (1, 'NFLX',  'Netflix Inc.',                 'Communication',     'Entertainment',          'NASDAQ'),
    (1, 'ABNB',  'Airbnb Inc.',                  'Consumer Cyclical', 'Travel & Leisure',       'NASDAQ'),
    (1, 'BKNG',  'Booking Holdings Inc.',        'Consumer Cyclical', 'Travel & Leisure',       'NASDAQ'),
    (1, 'CMG',   'Chipotle Mexican Grill Inc.',  'Consumer Cyclical', 'Restaurants',            'NYSE'),
    (1, 'YUM',   'Yum! Brands Inc.',             'Consumer Cyclical', 'Restaurants',            'NYSE'),
    (1, 'DPZ',   'Domino''s Pizza Inc.',         'Consumer Cyclical', 'Restaurants',            'NYSE'),
    (1, 'LULU',  'Lululemon Athletica Inc.',     'Consumer Cyclical', 'Apparel',                'NASDAQ'),
    (1, 'TJX',   'TJX Companies Inc.',           'Consumer Cyclical', 'Apparel Retail',         'NYSE'),

    -- ── Stocks: Industrials ────────────────────────────────────────────────────
    (1, 'CAT',   'Caterpillar Inc.',             'Industrials',       'Farm & Heavy Machinery', 'NYSE'),
    (1, 'BA',    'Boeing Co.',                   'Industrials',       'Aerospace & Defense',    'NYSE'),
    (1, 'UNP',   'Union Pacific Corp.',          'Industrials',       'Railroads',              'NYSE'),
    (1, 'HON',   'Honeywell International Inc.', 'Industrials',       'Conglomerates',          'NASDAQ'),
    (1, 'DE',    'Deere & Co.',                  'Industrials',       'Farm & Heavy Machinery', 'NYSE'),
    (1, 'GE',    'GE Aerospace',                 'Industrials',       'Aerospace & Defense',    'NYSE'),
    (1, 'LMT',   'Lockheed Martin Corp.',        'Industrials',       'Aerospace & Defense',    'NYSE'),
    (1, 'RTX',   'RTX Corp.',                    'Industrials',       'Aerospace & Defense',    'NYSE'),
    (1, 'UPS',   'United Parcel Service Inc.',   'Industrials',       'Shipping & Logistics',   'NYSE'),
    (1, 'FDX',   'FedEx Corp.',                  'Industrials',       'Shipping & Logistics',   'NYSE'),
    (1, 'MMM',   '3M Co.',                       'Industrials',       'Conglomerates',          'NYSE'),
    (1, 'EMR',   'Emerson Electric Co.',         'Industrials',       'Electrical Equipment',   'NYSE'),
    (1, 'ITW',   'Illinois Tool Works Inc.',     'Industrials',       'Specialty Industrials',  'NYSE'),
    (1, 'ETN',   'Eaton Corp. PLC',              'Industrials',       'Electrical Equipment',   'NYSE'),
    (1, 'PH',    'Parker-Hannifin Corp.',        'Industrials',       'Specialty Industrials',  'NYSE'),
    (1, 'ROK',   'Rockwell Automation Inc.',     'Industrials',       'Electrical Equipment',   'NYSE'),
    (1, 'FAST',  'Fastenal Co.',                 'Industrials',       'Industrial Distribution', 'NASDAQ'),

    -- ── Stocks: Energy ─────────────────────────────────────────────────────────
    (1, 'XOM',   'Exxon Mobil Corp.',            'Energy',            'Oil & Gas Integrated',   'NYSE'),
    (1, 'CVX',   'Chevron Corp.',                'Energy',            'Oil & Gas Integrated',   'NYSE'),
    (1, 'COP',   'ConocoPhillips',               'Energy',            'Oil & Gas E&P',          'NYSE'),
    (1, 'SLB',   'Schlumberger Ltd.',            'Energy',            'Oil & Gas Services',     'NYSE'),
    (1, 'EOG',   'EOG Resources Inc.',           'Energy',            'Oil & Gas E&P',          'NYSE'),
    (1, 'MPC',   'Marathon Petroleum Corp.',     'Energy',            'Oil & Gas Refining',     'NYSE'),
    (1, 'VLO',   'Valero Energy Corp.',          'Energy',            'Oil & Gas Refining',     'NYSE'),
    (1, 'PSX',   'Phillips 66',                  'Energy',            'Oil & Gas Refining',     'NYSE'),
    (1, 'OXY',   'Occidental Petroleum Corp.',   'Energy',            'Oil & Gas E&P',          'NYSE'),
    (1, 'HAL',   'Halliburton Co.',              'Energy',            'Oil & Gas Services',     'NYSE'),
    (1, 'DVN',   'Devon Energy Corp.',           'Energy',            'Oil & Gas E&P',          'NYSE'),
    (1, 'FANG',  'Diamondback Energy Inc.',      'Energy',            'Oil & Gas E&P',          'NASDAQ'),
    (1, 'PXD',   'Pioneer Natural Resources Co.','Energy',            'Oil & Gas E&P',          'NYSE'),

    -- ── Stocks: REITs ──────────────────────────────────────────────────────────
    (1, 'AMT',   'American Tower Corp.',         'Real Estate',       'REIT - Specialty',       'NYSE'),
    (1, 'PLD',   'Prologis Inc.',                'Real Estate',       'REIT - Industrial',      'NYSE'),
    (1, 'CCI',   'Crown Castle Inc.',            'Real Estate',       'REIT - Specialty',       'NYSE'),
    (1, 'EQIX',  'Equinix Inc.',                 'Real Estate',       'REIT - Data Centers',    'NASDAQ'),
    (1, 'SPG',   'Simon Property Group Inc.',    'Real Estate',       'REIT - Retail',          'NYSE'),
    (1, 'O',     'Realty Income Corp.',           'Real Estate',       'REIT - Retail',          'NYSE'),
    (1, 'DLR',   'Digital Realty Trust Inc.',    'Real Estate',       'REIT - Data Centers',    'NYSE'),
    (1, 'PSA',   'Public Storage',               'Real Estate',       'REIT - Storage',         'NYSE'),
    (1, 'WELL',  'Welltower Inc.',               'Real Estate',       'REIT - Healthcare',      'NYSE'),
    (1, 'AVB',   'AvalonBay Communities Inc.',   'Real Estate',       'REIT - Residential',     'NYSE'),
    (1, 'EQR',   'Equity Residential',           'Real Estate',       'REIT - Residential',     'NYSE'),

    -- ── Stocks: Utilities ──────────────────────────────────────────────────────
    (1, 'NEE',   'NextEra Energy Inc.',          'Utilities',         'Utilities - Renewables', 'NYSE'),
    (1, 'DUK',   'Duke Energy Corp.',            'Utilities',         'Utilities - Regulated',  'NYSE'),
    (1, 'SO',    'Southern Co.',                 'Utilities',         'Utilities - Regulated',  'NYSE'),
    (1, 'D',     'Dominion Energy Inc.',         'Utilities',         'Utilities - Regulated',  'NYSE'),
    (1, 'AEP',   'American Electric Power Co.',  'Utilities',         'Utilities - Regulated',  'NASDAQ'),
    (1, 'SRE',   'Sempra',                       'Utilities',         'Utilities - Diversified','NYSE'),
    (1, 'EXC',   'Exelon Corp.',                 'Utilities',         'Utilities - Regulated',  'NASDAQ'),
    (1, 'XEL',   'Xcel Energy Inc.',             'Utilities',         'Utilities - Regulated',  'NASDAQ'),
    (1, 'ED',    'Consolidated Edison Inc.',     'Utilities',         'Utilities - Regulated',  'NYSE'),
    (1, 'WEC',   'WEC Energy Group Inc.',        'Utilities',         'Utilities - Regulated',  'NYSE'),

    -- ── Stocks: Materials ──────────────────────────────────────────────────────
    (1, 'LIN',   'Linde PLC',                    'Materials',         'Specialty Chemicals',    'NYSE'),
    (1, 'APD',   'Air Products & Chemicals Inc.','Materials',         'Specialty Chemicals',    'NYSE'),
    (1, 'SHW',   'Sherwin-Williams Co.',         'Materials',         'Specialty Chemicals',    'NYSE'),
    (1, 'ECL',   'Ecolab Inc.',                  'Materials',         'Specialty Chemicals',    'NYSE'),
    (1, 'NEM',   'Newmont Corp.',                'Materials',         'Gold Mining',            'NYSE'),
    (1, 'FCX',   'Freeport-McMoRan Inc.',        'Materials',         'Copper Mining',          'NYSE'),
    (1, 'CTVA',  'Corteva Inc.',                 'Materials',         'Agricultural Chemicals', 'NYSE'),
    (1, 'DD',    'DuPont de Nemours Inc.',       'Materials',         'Specialty Chemicals',    'NYSE'),
    (1, 'NUE',   'Nucor Corp.',                  'Materials',         'Steel',                  'NYSE'),
    (1, 'STLD',  'Steel Dynamics Inc.',          'Materials',         'Steel',                  'NASDAQ'),

    -- ── Stocks: Communication Services ─────────────────────────────────────────
    (1, 'T',     'AT&T Inc.',                    'Communication',     'Telecom',                'NYSE'),
    (1, 'VZ',    'Verizon Communications Inc.',  'Communication',     'Telecom',                'NYSE'),
    (1, 'CMCSA', 'Comcast Corp.',                'Communication',     'Telecom',                'NASDAQ'),
    (1, 'TMUS',  'T-Mobile US Inc.',             'Communication',     'Telecom',                'NASDAQ'),
    (1, 'CHTR',  'Charter Communications Inc.',  'Communication',     'Telecom',                'NASDAQ'),

    -- ── Stocks: ETFs ───────────────────────────────────────────────────────────
    (1, 'SPY',   'SPDR S&P 500 ETF Trust',      'ETF',               'Index - Large Cap',      'NYSE'),
    (1, 'QQQ',   'Invesco QQQ Trust',            'ETF',               'Index - Tech',           'NASDAQ'),
    (1, 'DIA',   'SPDR Dow Jones Industrial ETF','ETF',               'Index - Large Cap',      'NYSE'),
    (1, 'IWM',   'iShares Russell 2000 ETF',    'ETF',               'Index - Small Cap',      'NYSE'),
    (1, 'VTI',   'Vanguard Total Stock Market ETF','ETF',             'Index - Total Market',   'NYSE'),
    (1, 'VOO',   'Vanguard S&P 500 ETF',        'ETF',               'Index - Large Cap',      'NYSE'),
    (1, 'ARKK',  'ARK Innovation ETF',           'ETF',               'Thematic - Innovation',  'NYSE'),
    (1, 'XLF',   'Financial Select Sector SPDR', 'ETF',               'Sector - Financial',     'NYSE'),
    (1, 'XLE',   'Energy Select Sector SPDR',    'ETF',               'Sector - Energy',        'NYSE'),
    (1, 'XLK',   'Technology Select Sector SPDR','ETF',               'Sector - Technology',    'NYSE'),
    (1, 'XLV',   'Health Care Select Sector SPDR','ETF',              'Sector - Healthcare',    'NYSE'),
    (1, 'XLI',   'Industrial Select Sector SPDR','ETF',               'Sector - Industrials',   'NYSE'),
    (1, 'GLD',   'SPDR Gold Shares',             'ETF',               'Commodity - Gold',       'NYSE'),
    (1, 'SLV',   'iShares Silver Trust',         'ETF',               'Commodity - Silver',     'NYSE'),
    (1, 'TLT',   'iShares 20+ Year Treasury ETF','ETF',               'Fixed Income - Long',    'NASDAQ'),
    (1, 'HYG',   'iShares iBoxx High Yield ETF','ETF',               'Fixed Income - HY',      'NYSE'),
    (1, 'IBIT',  'iShares Bitcoin Trust',        'ETF',               'Crypto - Bitcoin',       'NASDAQ'),
    (1, 'ETHA',  'iShares Ethereum Trust',       'ETF',               'Crypto - Ethereum',      'NASDAQ'),

    -- ── Stocks: Additional Tech & Growth ───────────────────────────────────────
    (1, 'PYPL',  'PayPal Holdings Inc.',         'Technology',        'Fintech',                'NASDAQ'),
    (1, 'UBER',  'Uber Technologies Inc.',       'Technology',        'Software - Application', 'NYSE'),
    (1, 'COIN',  'Coinbase Global Inc.',         'Financial',         'Fintech',                'NASDAQ'),
    (1, 'HOOD',  'Robinhood Markets Inc.',       'Financial',         'Fintech',                'NASDAQ'),
    (1, 'SOFI',  'SoFi Technologies Inc.',       'Financial',         'Fintech',                'NASDAQ'),
    (1, 'ROKU',  'Roku Inc.',                    'Communication',     'Entertainment',          'NASDAQ'),
    (1, 'SNAP',  'Snap Inc.',                    'Communication',     'Internet Services',      'NYSE'),
    (1, 'PINS',  'Pinterest Inc.',               'Communication',     'Internet Services',      'NYSE'),
    (1, 'TWLO',  'Twilio Inc.',                  'Technology',        'Software',               'NYSE'),
    (1, 'OKTA',  'Okta Inc.',                    'Technology',        'Cybersecurity',          'NASDAQ'),
    (1, 'DOCU',  'DocuSign Inc.',                'Technology',        'Software',               'NASDAQ'),
    (1, 'ZM',    'Zoom Video Communications',    'Technology',        'Software',               'NASDAQ'),
    (1, 'DASH',  'DoorDash Inc.',                'Consumer Cyclical', 'Internet Services',      'NASDAQ'),
    (1, 'RIVN',  'Rivian Automotive Inc.',       'Consumer Cyclical', 'Auto Manufacturers',     'NASDAQ'),
    (1, 'LCID',  'Lucid Group Inc.',             'Consumer Cyclical', 'Auto Manufacturers',     'NASDAQ'),
    (1, 'PATH',  'UiPath Inc.',                  'Technology',        'Software',               'NYSE'),
    (1, 'U',     'Unity Software Inc.',          'Technology',        'Software',               'NYSE'),
    (1, 'RBLX',  'Roblox Corp.',                 'Communication',     'Gaming',                 'NYSE'),
    (1, 'TTWO',  'Take-Two Interactive Software','Communication',     'Gaming',                 'NASDAQ'),
    (1, 'EA',    'Electronic Arts Inc.',         'Communication',     'Gaming',                 'NASDAQ'),
    (1, 'ATVI',  'Activision Blizzard Inc.',     'Communication',     'Gaming',                 'NASDAQ'),
    (1, 'MRVL',  'Marvell Technology Inc.',      'Technology',        'Semiconductors',         'NASDAQ'),
    (1, 'ON',    'ON Semiconductor Corp.',       'Technology',        'Semiconductors',         'NASDAQ'),
    (1, 'MU',    'Micron Technology Inc.',       'Technology',        'Semiconductors',         'NASDAQ'),
    (1, 'AMAT',  'Applied Materials Inc.',       'Technology',        'Semiconductor Equipment','NASDAQ'),
    (1, 'LRCX',  'Lam Research Corp.',           'Technology',        'Semiconductor Equipment','NASDAQ'),
    (1, 'KLAC',  'KLA Corp.',                    'Technology',        'Semiconductor Equipment','NASDAQ'),
    (1, 'ASML',  'ASML Holding NV',             'Technology',        'Semiconductor Equipment','NASDAQ'),
    (1, 'ADI',   'Analog Devices Inc.',          'Technology',        'Semiconductors',         'NASDAQ'),
    (1, 'NXPI',  'NXP Semiconductors NV',       'Technology',        'Semiconductors',         'NASDAQ'),
    (1, 'WDAY',  'Workday Inc.',                 'Technology',        'Software',               'NASDAQ'),
    (1, 'VEEV',  'Veeva Systems Inc.',           'Technology',        'Software',               'NYSE'),
    (1, 'TEAM',  'Atlassian Corp.',              'Technology',        'Software',               'NASDAQ'),
    (1, 'HUBS',  'HubSpot Inc.',                 'Technology',        'Software',               'NYSE'),
    (1, 'BILL',  'BILL Holdings Inc.',           'Technology',        'Fintech',                'NYSE'),
    (1, 'CELH',  'Celsius Holdings Inc.',        'Consumer Defensive','Beverages',              'NASDAQ'),
    (1, 'MNST',  'Monster Beverage Corp.',       'Consumer Defensive','Beverages',              'NASDAQ'),
    (1, 'CL',    'Colgate-Palmolive Co.',        'Consumer Defensive','Household Products',     'NYSE'),
    (1, 'EL',    'Estee Lauder Companies Inc.',  'Consumer Defensive','Personal Products',      'NYSE'),
    (1, 'CPRT',  'Copart Inc.',                  'Industrials',       'Specialty Industrials',  'NASDAQ'),
    (1, 'ODFL',  'Old Dominion Freight Line',    'Industrials',       'Shipping & Logistics',   'NASDAQ'),
    (1, 'GWW',   'W.W. Grainger Inc.',           'Industrials',       'Industrial Distribution','NYSE'),

    -- ── Crypto: Layer 1 ────────────────────────────────────────────────────────
    (2, 'BTC',   'Bitcoin',                      'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'ETH',   'Ethereum',                     'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'SOL',   'Solana',                       'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'ADA',   'Cardano',                      'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'AVAX',  'Avalanche',                    'Cryptocurrency',    'Layer 1',                'Coinbase'),
    (2, 'DOT',   'Polkadot',                     'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'ATOM',  'Cosmos',                       'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'NEAR',  'NEAR Protocol',                'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'APT',   'Aptos',                        'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'SUI',   'Sui',                          'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'SEI',   'Sei',                          'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'TIA',   'Celestia',                     'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'INJ',   'Injective',                    'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'FTM',   'Fantom',                       'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'ALGO',  'Algorand',                     'Cryptocurrency',    'Layer 1',                'Coinbase'),
    (2, 'XTZ',   'Tezos',                        'Cryptocurrency',    'Layer 1',                'Coinbase'),
    (2, 'EGLD',  'MultiversX',                   'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'HBAR',  'Hedera',                       'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'ICP',   'Internet Computer',            'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'FIL',   'Filecoin',                     'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'AR',    'Arweave',                      'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'ROSE',  'Oasis Network',                'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'MINA',  'Mina Protocol',                'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'CKB',   'Nervos Network',               'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'KAS',   'Kaspa',                        'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'TAO',   'Bittensor',                    'Cryptocurrency',    'Layer 1',                'Binance'),

    -- ── Crypto: Layer 2 ────────────────────────────────────────────────────────
    (2, 'MATIC', 'Polygon',                      'Cryptocurrency',    'Layer 2',                'Binance'),
    (2, 'OP',    'Optimism',                     'Cryptocurrency',    'Layer 2',                'Binance'),
    (2, 'ARB',   'Arbitrum',                     'Cryptocurrency',    'Layer 2',                'Binance'),
    (2, 'STRK',  'Starknet',                     'Cryptocurrency',    'Layer 2',                'Binance'),
    (2, 'ZK',    'ZKsync',                       'Cryptocurrency',    'Layer 2',                'Binance'),
    (2, 'MNT',   'Mantle',                       'Cryptocurrency',    'Layer 2',                'Binance'),
    (2, 'METIS', 'Metis',                        'Cryptocurrency',    'Layer 2',                'Binance'),
    (2, 'IMX',   'Immutable',                    'Cryptocurrency',    'Layer 2',                'Binance'),
    (2, 'LRC',   'Loopring',                     'Cryptocurrency',    'Layer 2',                'Coinbase'),
    (2, 'BOBA',  'Boba Network',                 'Cryptocurrency',    'Layer 2',                'Binance'),

    -- ── Crypto: DeFi ───────────────────────────────────────────────────────────
    (2, 'UNI',   'Uniswap',                      'Cryptocurrency',    'DeFi',                   'Coinbase'),
    (2, 'AAVE',  'Aave',                         'Cryptocurrency',    'DeFi',                   'Coinbase'),
    (2, 'MKR',   'Maker',                        'Cryptocurrency',    'DeFi',                   'Coinbase'),
    (2, 'SNX',   'Synthetix',                    'Cryptocurrency',    'DeFi',                   'Coinbase'),
    (2, 'CRV',   'Curve DAO',                    'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'COMP',  'Compound',                     'Cryptocurrency',    'DeFi',                   'Coinbase'),
    (2, 'SUSHI', 'SushiSwap',                    'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'YFI',   'yearn.finance',                'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'BAL',   'Balancer',                     'Cryptocurrency',    'DeFi',                   'Coinbase'),
    (2, 'DYDX',  'dYdX',                         'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'GMX',   'GMX',                          'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'PENDLE','Pendle',                       'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'JUP',   'Jupiter',                      'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'RAY',   'Raydium',                      'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'ORCA',  'Orca',                         'Cryptocurrency',    'DeFi',                   'Coinbase'),
    (2, 'JTO',   'Jito',                         'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'PYTH',  'Pyth Network',                 'Cryptocurrency',    'DeFi',                   'Binance'),

    -- ── Crypto: Exchange Tokens ────────────────────────────────────────────────
    (2, 'BNB',   'BNB',                          'Cryptocurrency',    'Exchange Token',         'Binance'),
    (2, 'OKB',   'OKB',                          'Cryptocurrency',    'Exchange Token',         'OKX'),
    (2, 'CRO',   'Cronos',                       'Cryptocurrency',    'Exchange Token',         'Binance'),
    (2, 'KCS',   'KuCoin Token',                 'Cryptocurrency',    'Exchange Token',         'KuCoin'),
    (2, 'GT',    'Gate Token',                   'Cryptocurrency',    'Exchange Token',         'Gate.io'),
    (2, 'HT',    'Huobi Token',                  'Cryptocurrency',    'Exchange Token',         'Binance'),
    (2, 'LEO',   'UNUS SED LEO',                'Cryptocurrency',    'Exchange Token',         'Binance'),
    (2, 'FTT',   'FTX Token',                    'Cryptocurrency',    'Exchange Token',         'Binance'),
    (2, 'MX',    'MX Token',                     'Cryptocurrency',    'Exchange Token',         'Binance'),

    -- ── Crypto: Payments ───────────────────────────────────────────────────────
    (2, 'XRP',   'XRP',                          'Cryptocurrency',    'Payments',               'Binance'),
    (2, 'XLM',   'Stellar',                      'Cryptocurrency',    'Payments',               'Coinbase'),
    (2, 'XNO',   'Nano',                         'Cryptocurrency',    'Payments',               'Binance'),

    -- ── Crypto: Meme ───────────────────────────────────────────────────────────
    (2, 'DOGE',  'Dogecoin',                     'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'SHIB',  'Shiba Inu',                    'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'PEPE',  'Pepe',                         'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'WIF',   'dogwifhat',                    'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'BONK',  'Bonk',                         'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'FLOKI', 'Floki',                        'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'MEME',  'Memecoin',                     'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'BRETT', 'Brett',                        'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'MOG',   'Mog Coin',                     'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'POPCAT','Popcat',                       'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'TURBO', 'Turbo',                        'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'NEIRO', 'Neiro',                        'Cryptocurrency',    'Meme',                   'Binance'),

    -- ── Crypto: Gaming & Metaverse ─────────────────────────────────────────────
    (2, 'AXS',   'Axie Infinity',                'Cryptocurrency',    'Gaming',                 'Binance'),
    (2, 'SAND',  'The Sandbox',                  'Cryptocurrency',    'Gaming',                 'Binance'),
    (2, 'MANA',  'Decentraland',                 'Cryptocurrency',    'Gaming',                 'Coinbase'),
    (2, 'GALA',  'Gala',                         'Cryptocurrency',    'Gaming',                 'Binance'),
    (2, 'ENJ',   'Enjin Coin',                   'Cryptocurrency',    'Gaming',                 'Coinbase'),
    (2, 'ILV',   'Illuvium',                     'Cryptocurrency',    'Gaming',                 'Binance'),
    (2, 'PRIME', 'Echelon Prime',                'Cryptocurrency',    'Gaming',                 'Coinbase'),
    (2, 'BEAM',  'Beam',                         'Cryptocurrency',    'Gaming',                 'Binance'),
    (2, 'PIXEL', 'Pixels',                       'Cryptocurrency',    'Gaming',                 'Binance'),
    (2, 'PORTAL','Portal',                       'Cryptocurrency',    'Gaming',                 'Binance'),
    (2, 'RONIN', 'Ronin',                        'Cryptocurrency',    'Gaming',                 'Binance'),

    -- ── Crypto: AI ─────────────────────────────────────────────────────────────
    (2, 'RNDR',  'Render',                       'Cryptocurrency',    'AI',                     'Binance'),
    (2, 'FET',   'Fetch.ai',                     'Cryptocurrency',    'AI',                     'Binance'),
    (2, 'AGIX',  'SingularityNET',               'Cryptocurrency',    'AI',                     'Binance'),
    (2, 'OCEAN', 'Ocean Protocol',               'Cryptocurrency',    'AI',                     'Binance'),
    (2, 'AKT',   'Akash Network',                'Cryptocurrency',    'AI',                     'Binance'),
    (2, 'AIOZ',  'AIOZ Network',                 'Cryptocurrency',    'AI',                     'Binance'),
    (2, 'LPT',   'Livepeer',                     'Cryptocurrency',    'AI',                     'Coinbase'),
    (2, 'GLM',   'Golem',                        'Cryptocurrency',    'AI',                     'Binance'),

    -- ── Crypto: Storage & Compute ──────────────────────────────────────────────
    (2, 'STORJ', 'Storj',                        'Cryptocurrency',    'Storage',                'Coinbase'),
    (2, 'SC',    'Siacoin',                      'Cryptocurrency',    'Storage',                'Binance'),
    (2, 'HNT',   'Helium',                       'Cryptocurrency',    'IoT',                    'Coinbase'),
    (2, 'IOTX',  'IoTeX',                        'Cryptocurrency',    'IoT',                    'Binance'),
    (2, 'THETA', 'Theta Network',                'Cryptocurrency',    'Streaming',              'Binance'),

    -- ── Crypto: Privacy ────────────────────────────────────────────────────────
    (2, 'XMR',   'Monero',                       'Cryptocurrency',    'Privacy',                'Binance'),
    (2, 'ZEC',   'Zcash',                        'Cryptocurrency',    'Privacy',                'Coinbase'),
    (2, 'DASH',  'Dash',                         'Cryptocurrency',    'Privacy',                'Binance'),
    (2, 'SCRT',  'Secret',                       'Cryptocurrency',    'Privacy',                'Binance'),

    -- ── Crypto: Oracles ────────────────────────────────────────────────────────
    (2, 'LINK',  'Chainlink',                    'Cryptocurrency',    'Oracle',                 'Coinbase'),
    (2, 'BAND',  'Band Protocol',                'Cryptocurrency',    'Oracle',                 'Binance'),
    (2, 'API3',  'API3',                         'Cryptocurrency',    'Oracle',                 'Binance'),
    (2, 'UMA',   'UMA',                          'Cryptocurrency',    'Oracle',                 'Coinbase'),

    -- ── Crypto: Stablecoins (reference) ────────────────────────────────────────
    (2, 'USDT',  'Tether',                       'Cryptocurrency',    'Stablecoin',             'Binance'),
    (2, 'USDC',  'USD Coin',                     'Cryptocurrency',    'Stablecoin',             'Coinbase'),
    (2, 'DAI',   'Dai',                          'Cryptocurrency',    'Stablecoin',             'Coinbase'),
    (2, 'FRAX',  'Frax',                         'Cryptocurrency',    'Stablecoin',             'Binance'),
    (2, 'TUSD',  'TrueUSD',                      'Cryptocurrency',    'Stablecoin',             'Binance'),

    -- ── Crypto: Wrapped & Liquid Staking ───────────────────────────────────────
    (2, 'WBTC',  'Wrapped Bitcoin',              'Cryptocurrency',    'Wrapped',                'Binance'),
    (2, 'WETH',  'Wrapped Ether',                'Cryptocurrency',    'Wrapped',                'Binance'),
    (2, 'STETH', 'Lido Staked Ether',            'Cryptocurrency',    'Liquid Staking',         'Binance'),
    (2, 'RETH',  'Rocket Pool ETH',              'Cryptocurrency',    'Liquid Staking',         'Binance'),
    (2, 'CBETH', 'Coinbase Wrapped Staked ETH',  'Cryptocurrency',    'Liquid Staking',         'Coinbase'),
    (2, 'MSOL',  'Marinade Staked SOL',          'Cryptocurrency',    'Liquid Staking',         'Binance'),
    (2, 'JITOSOL','Jito Staked SOL',             'Cryptocurrency',    'Liquid Staking',         'Binance'),

    -- ── Crypto: Additional Layer 1s ────────────────────────────────────────────
    (2, 'EOS',   'EOS',                          'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'NEO',   'Neo',                          'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'VET',   'VeChain',                      'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'ONE',   'Harmony',                      'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'FLOW',  'Flow',                         'Cryptocurrency',    'Layer 1',                'Coinbase'),
    (2, 'KAVA',  'Kava',                         'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'CELO',  'Celo',                         'Cryptocurrency',    'Layer 1',                'Coinbase'),
    (2, 'CFX',   'Conflux',                      'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'ASTR',  'Astar',                        'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'GLMR',  'Moonbeam',                     'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'MOVR',  'Moonriver',                    'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'OSMO',  'Osmosis',                      'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'RUNE',  'THORChain',                    'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'IOTA',  'IOTA',                         'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'ZIL',   'Zilliqa',                      'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'QTUM',  'Qtum',                         'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'WAVES', 'Waves',                        'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'XDC',   'XDC Network',                  'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'TONCOIN','Toncoin',                     'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'TRX',   'TRON',                         'Cryptocurrency',    'Layer 1',                'Binance'),
    (2, 'ETC',   'Ethereum Classic',             'Cryptocurrency',    'Layer 1',                'Coinbase'),
    (2, 'LTC',   'Litecoin',                     'Cryptocurrency',    'Layer 1',                'Coinbase'),
    (2, 'BCH',   'Bitcoin Cash',                 'Cryptocurrency',    'Layer 1',                'Coinbase'),

    -- ── Crypto: Additional DeFi ────────────────────────────────────────────────
    (2, 'CAKE',  'PancakeSwap',                  'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'LDO',   'Lido DAO',                     'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'RPL',   'Rocket Pool',                  'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'FXS',   'Frax Share',                   'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'SPELL', 'Spell Token',                  'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'LQTY',  'Liquity',                      'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'RDNT',  'Radiant Capital',              'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'SSV',   'SSV Network',                  'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'ETHFI', 'Ether.fi',                     'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'ENA',   'Ethena',                       'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'EIGEN', 'EigenLayer',                   'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'W',     'Wormhole',                     'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, '1INCH', '1inch Network',                'Cryptocurrency',    'DeFi',                   'Binance'),
    (2, 'ANKR',  'Ankr',                         'Cryptocurrency',    'DeFi',                   'Coinbase'),

    -- ── Crypto: Additional Infrastructure ──────────────────────────────────────
    (2, 'GRT',   'The Graph',                    'Cryptocurrency',    'Infrastructure',         'Coinbase'),
    (2, 'STX',   'Stacks',                       'Cryptocurrency',    'Infrastructure',         'Binance'),
    (2, 'QNT',   'Quant',                        'Cryptocurrency',    'Infrastructure',         'Binance'),
    (2, 'FLUX',  'Flux',                         'Cryptocurrency',    'Infrastructure',         'Binance'),
    (2, 'RVN',   'Ravencoin',                    'Cryptocurrency',    'Infrastructure',         'Binance'),
    (2, 'ENS',   'Ethereum Name Service',        'Cryptocurrency',    'Infrastructure',         'Coinbase'),
    (2, 'CHZ',   'Chiliz',                       'Cryptocurrency',    'Infrastructure',         'Binance'),
    (2, 'MASK',  'Mask Network',                 'Cryptocurrency',    'Infrastructure',         'Binance'),
    (2, 'COTI',  'COTI',                         'Cryptocurrency',    'Infrastructure',         'Binance'),
    (2, 'SKL',   'SKALE',                        'Cryptocurrency',    'Infrastructure',         'Coinbase'),

    -- ── Crypto: Additional Meme & Social ───────────────────────────────────────
    (2, 'LUNC',  'Terra Classic',                'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'APE',   'ApeCoin',                      'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'PEOPLE','ConstitutionDAO',              'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'BOME',  'Book of Meme',                 'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'MEW',   'cat in a dogs world',          'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'MYRO',  'Myro',                         'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'SLERF', 'Slerf',                        'Cryptocurrency',    'Meme',                   'Binance'),
    (2, 'TNSR',  'Tensor',                       'Cryptocurrency',    'NFT',                    'Binance'),
    (2, 'BLUR',  'Blur',                         'Cryptocurrency',    'NFT',                    'Binance'),
    (2, 'SUPER', 'SuperVerse',                   'Cryptocurrency',    'Gaming',                 'Binance'),
    (2, 'YGG',   'Yield Guild Games',            'Cryptocurrency',    'Gaming',                 'Binance'),
    (2, 'ALICE', 'My Neighbor Alice',            'Cryptocurrency',    'Gaming',                 'Binance'),

    -- ── Crypto: Cross-chain & Bridges ──────────────────────────────────────────
    (2, 'WORMHOLE','Wormhole Bridge Token',      'Cryptocurrency',    'Bridge',                 'Binance'),
    (2, 'AXL',   'Axelar',                       'Cryptocurrency',    'Bridge',                 'Binance'),
    (2, 'ZRO',   'LayerZero',                    'Cryptocurrency',    'Bridge',                 'Binance'),
    (2, 'ACX',   'Across Protocol',              'Cryptocurrency',    'Bridge',                 'Binance'),
    (2, 'CCIP',  'Chainlink CCIP Token',         'Cryptocurrency',    'Bridge',                 'Binance'),
    (2, 'SYNAPSE','Synapse',                     'Cryptocurrency',    'Bridge',                 'Binance')
ON CONFLICT (asset_class_id, ticker) DO NOTHING;
