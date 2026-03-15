-- Pipeline stage execution tracking
-- Equivalent to sports-data-admin's game_pipeline_stages table
--
-- Records individual stage runs within a pipeline job execution,
-- giving visibility into which stage failed and why.

CREATE TABLE IF NOT EXISTS fin_pipeline_stage_runs (
    id              SERIAL PRIMARY KEY,
    job_run_id      INTEGER NOT NULL REFERENCES fin_job_runs(id) ON DELETE CASCADE,
    stage           VARCHAR(50) NOT NULL,
        -- collect_candles, compute_indicators, validate_data, detect_events,
        -- analyze_sentiment, generate_narrative, validate_narrative, finalize
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- pending, running, completed, failed, skipped
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    duration_ms     REAL,
    output_json     JSONB,
    error_details   TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pipeline_stages_job_run
    ON fin_pipeline_stage_runs(job_run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_stages_stage
    ON fin_pipeline_stage_runs(stage);
CREATE INDEX IF NOT EXISTS idx_pipeline_stages_status
    ON fin_pipeline_stage_runs(status);
