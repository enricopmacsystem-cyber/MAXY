-- Chat interna tra utenti Maxy AI (team Mac System)

CREATE TABLE IF NOT EXISTS internal_chat_messages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel             VARCHAR(80) NOT NULL DEFAULT 'generale',
    sender_user_id      VARCHAR(100) NOT NULL,
    sender_username     VARCHAR(120) NOT NULL,
    sender_display_name VARCHAR(200) NOT NULL,
    body                TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_internal_chat_channel_created
    ON internal_chat_messages (channel, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_internal_chat_sender
    ON internal_chat_messages (sender_user_id);
