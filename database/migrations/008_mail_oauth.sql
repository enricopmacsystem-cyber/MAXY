-- Account posta OAuth (Gmail / Outlook) per utente EasyOne

CREATE TABLE IF NOT EXISTS mail_oauth_accounts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    easyone_user_id     VARCHAR(100) NOT NULL,
    provider            VARCHAR(20) NOT NULL,
    email_address       VARCHAR(320) NOT NULL,
    access_token        TEXT NOT NULL,
    refresh_token       TEXT,
    token_expires_at    TIMESTAMPTZ,
    scopes              TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mail_oauth_user_provider_email
        UNIQUE (easyone_user_id, provider, email_address)
);

CREATE INDEX IF NOT EXISTS idx_mail_oauth_user
    ON mail_oauth_accounts (easyone_user_id);
