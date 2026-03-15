-- =============================================================================
-- Seed Assets — Update top 30 stocks + top 15 crypto with external_ids
-- =============================================================================
-- Adds CoinGecko IDs, CMC IDs, and other external identifiers needed
-- by the scraper clients.

-- ── Crypto external_ids (CoinGecko + CMC IDs) ──────────────────────────────

UPDATE fin_assets SET external_ids = '{"coingecko_id": "bitcoin", "cmc_id": 1}'::jsonb
WHERE ticker = 'BTC' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "ethereum", "cmc_id": 1027}'::jsonb
WHERE ticker = 'ETH' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "binancecoin", "cmc_id": 1839}'::jsonb
WHERE ticker = 'BNB' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "solana", "cmc_id": 5426}'::jsonb
WHERE ticker = 'SOL' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "ripple", "cmc_id": 52}'::jsonb
WHERE ticker = 'XRP' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "cardano", "cmc_id": 2010}'::jsonb
WHERE ticker = 'ADA' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "dogecoin", "cmc_id": 74}'::jsonb
WHERE ticker = 'DOGE' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "avalanche-2", "cmc_id": 5805}'::jsonb
WHERE ticker = 'AVAX' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "polkadot", "cmc_id": 6636}'::jsonb
WHERE ticker = 'DOT' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "matic-network", "cmc_id": 3890}'::jsonb
WHERE ticker = 'MATIC' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "chainlink", "cmc_id": 1975}'::jsonb
WHERE ticker = 'LINK' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "uniswap", "cmc_id": 7083}'::jsonb
WHERE ticker = 'UNI' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "cosmos", "cmc_id": 3794}'::jsonb
WHERE ticker = 'ATOM' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "litecoin", "cmc_id": 2}'::jsonb
WHERE ticker = 'LTC' AND asset_class_id = 2;

UPDATE fin_assets SET external_ids = '{"coingecko_id": "aptos", "cmc_id": 21794}'::jsonb
WHERE ticker = 'APT' AND asset_class_id = 2;

-- ── Stock external_ids (yfinance ticker is the same, but add sector hints) ──

UPDATE fin_assets SET external_ids = '{"yfinance": "AAPL"}'::jsonb WHERE ticker = 'AAPL' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "MSFT"}'::jsonb WHERE ticker = 'MSFT' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "GOOGL"}'::jsonb WHERE ticker = 'GOOGL' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "AMZN"}'::jsonb WHERE ticker = 'AMZN' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "NVDA"}'::jsonb WHERE ticker = 'NVDA' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "META"}'::jsonb WHERE ticker = 'META' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "TSLA"}'::jsonb WHERE ticker = 'TSLA' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "BRK-B"}'::jsonb WHERE ticker = 'BRK-B' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "JPM"}'::jsonb WHERE ticker = 'JPM' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "V"}'::jsonb WHERE ticker = 'V' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "JNJ"}'::jsonb WHERE ticker = 'JNJ' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "WMT"}'::jsonb WHERE ticker = 'WMT' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "PG"}'::jsonb WHERE ticker = 'PG' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "MA"}'::jsonb WHERE ticker = 'MA' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "UNH"}'::jsonb WHERE ticker = 'UNH' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "HD"}'::jsonb WHERE ticker = 'HD' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "DIS"}'::jsonb WHERE ticker = 'DIS' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "NFLX"}'::jsonb WHERE ticker = 'NFLX' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "ADBE"}'::jsonb WHERE ticker = 'ADBE' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "CRM"}'::jsonb WHERE ticker = 'CRM' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "PYPL"}'::jsonb WHERE ticker = 'PYPL' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "INTC"}'::jsonb WHERE ticker = 'INTC' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "AMD"}'::jsonb WHERE ticker = 'AMD' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "COST"}'::jsonb WHERE ticker = 'COST' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "PEP"}'::jsonb WHERE ticker = 'PEP' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "KO"}'::jsonb WHERE ticker = 'KO' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "CSCO"}'::jsonb WHERE ticker = 'CSCO' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "ABT"}'::jsonb WHERE ticker = 'ABT' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "NKE"}'::jsonb WHERE ticker = 'NKE' AND asset_class_id = 1;
UPDATE fin_assets SET external_ids = '{"yfinance": "MRK"}'::jsonb WHERE ticker = 'MRK' AND asset_class_id = 1;
