-- Fase 1: autenticazione EasyOne, sessioni, audit, cache

CREATE TABLE IF NOT EXISTS user_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    easyone_user_id     VARCHAR(100) NOT NULL,
    easyone_username    VARCHAR(200) NOT NULL,
    display_name        VARCHAR(200),
    roles_json          JSONB NOT NULL DEFAULT '[]',
    permissions_json    JSONB NOT NULL DEFAULT '[]',
    token_hash          VARCHAR(64) NOT NULL,
    refresh_token_hash  VARCHAR(64),
    expires_at          TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_easyone_user
    ON user_sessions (easyone_user_id);

CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash
    ON user_sessions (token_hash);

CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh_hash
    ON user_sessions (refresh_token_hash)
    WHERE refresh_token_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_sessions_expires
    ON user_sessions (expires_at);

CREATE TABLE IF NOT EXISTS cache_entries (
    cache_key       VARCHAR(500) PRIMARY KEY,
    namespace       VARCHAR(100) NOT NULL,
    payload         JSONB NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    source_system   VARCHAR(50) NOT NULL,
    stale_after     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cache_namespace ON cache_entries (namespace);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries (expires_at);

CREATE TABLE IF NOT EXISTS audit_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID REFERENCES user_sessions(id) ON DELETE SET NULL,
    easyone_user_id     VARCHAR(100) NOT NULL,
    action              VARCHAR(100) NOT NULL,
    entity_type         VARCHAR(50),
    entity_id           VARCHAR(100),
    details             JSONB,
    ip_address          VARCHAR(45),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user_created
    ON audit_logs (easyone_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_action
    ON audit_logs (action, created_at DESC);
