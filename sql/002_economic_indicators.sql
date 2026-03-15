-- =============================================================================
-- Economic Indicators — FRED macro data (new table)
-- =============================================================================

CREATE TABLE IF NOT EXISTS fin_economic_indicators (
    id                  SERIAL PRIMARY KEY,
    series_id           VARCHAR(20) NOT NULL,
    series_name         VARCHAR(200) NOT NULL,
    category            VARCHAR(50) NOT NULL,
    value               DOUBLE PRECISION NOT NULL,
    observation_date    DATE NOT NULL,
    source              VARCHAR(50) DEFAULT 'fred',
    raw_data            JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (series_id, observation_date)
);

CREATE INDEX IF NOT EXISTS idx_econ_indicators_series ON fin_economic_indicators(series_id);
CREATE INDEX IF NOT EXISTS idx_econ_indicators_date ON fin_economic_indicators(observation_date);
CREATE INDEX IF NOT EXISTS idx_econ_indicators_category ON fin_economic_indicators(category);
