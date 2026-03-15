-- User accounts and preferences
-- Equivalent to sports-data-admin's user tables

CREATE TABLE IF NOT EXISTS fin_users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    display_name    VARCHAR(100),
    role            VARCHAR(20) NOT NULL DEFAULT 'viewer',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    magic_token     VARCHAR(255),
    magic_token_expires_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON fin_users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON fin_users(role);

CREATE TABLE IF NOT EXISTS fin_user_preferences (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES fin_users(id) ON DELETE CASCADE,
    key         VARCHAR(100) NOT NULL,
    value       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, key)
);

CREATE INDEX IF NOT EXISTS idx_user_prefs_user ON fin_user_preferences(user_id);
