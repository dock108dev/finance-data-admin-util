-- Analytics tables — ML models, feature configs, training, backtesting
-- Equivalent to sports-data-admin's analytics tables

CREATE TABLE IF NOT EXISTS fin_ml_models (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    model_type      VARCHAR(50) NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    asset_class     VARCHAR(20),
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    is_production   BOOLEAN NOT NULL DEFAULT FALSE,
    description     TEXT,
    hyperparameters JSONB,
    metrics         JSONB,
    artifact_path   VARCHAR(500),
    training_samples INTEGER,
    trained_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(name, version)
);

CREATE TABLE IF NOT EXISTS fin_feature_configs (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) UNIQUE NOT NULL,
    model_type      VARCHAR(50) NOT NULL,
    asset_class     VARCHAR(20),
    features        JSONB NOT NULL,
    scaler_type     VARCHAR(30),
    lookback_periods INTEGER NOT NULL DEFAULT 30,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fin_training_jobs (
    id              SERIAL PRIMARY KEY,
    model_id        INTEGER REFERENCES fin_ml_models(id),
    feature_config_id INTEGER REFERENCES fin_feature_configs(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    training_params JSONB,
    dataset_size    INTEGER,
    metrics         JSONB,
    error_details   TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    duration_seconds REAL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fin_backtest_jobs (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    signal_type     VARCHAR(50),
    asset_class     VARCHAR(20),
    start_date      VARCHAR(10),
    end_date        VARCHAR(10),
    params          JSONB,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    results         JSONB,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fin_prediction_outcomes (
    id                      SERIAL PRIMARY KEY,
    model_id                INTEGER REFERENCES fin_ml_models(id),
    signal_id               INTEGER REFERENCES fin_alpha_signals(id),
    asset_id                INTEGER REFERENCES fin_assets(id),
    predicted_direction     VARCHAR(10),
    predicted_confidence    REAL,
    actual_outcome          VARCHAR(20),
    actual_return_pct       REAL,
    prediction_date         VARCHAR(10),
    resolution_date         VARCHAR(10),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_models_type ON fin_ml_models(model_type);
CREATE INDEX IF NOT EXISTS idx_models_active ON fin_ml_models(is_active);
CREATE INDEX IF NOT EXISTS idx_feature_configs_type ON fin_feature_configs(model_type);
CREATE INDEX IF NOT EXISTS idx_training_jobs_status ON fin_training_jobs(status);
CREATE INDEX IF NOT EXISTS idx_backtest_status ON fin_backtest_jobs(status);
CREATE INDEX IF NOT EXISTS idx_predictions_model ON fin_prediction_outcomes(model_id);
CREATE INDEX IF NOT EXISTS idx_predictions_date ON fin_prediction_outcomes(prediction_date);
