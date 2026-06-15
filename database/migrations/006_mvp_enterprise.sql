-- MVP Enterprise: clienti cache, documenti, WhatsApp, aggiornamenti

CREATE TABLE IF NOT EXISTS customer_cache (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_code   VARCHAR(50) NOT NULL UNIQUE,
    company_name    VARCHAR(300) NOT NULL,
    vat_number      VARCHAR(20),
    phone           VARCHAR(30),
    email           VARCHAR(200),
    city            VARCHAR(100),
    sales_agent     VARCHAR(100),
    source_system   VARCHAR(50) NOT NULL DEFAULT 'local',
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customer_cache_company
    ON customer_cache USING gin (company_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_customer_cache_phone
    ON customer_cache (phone);

CREATE TABLE IF NOT EXISTS document_index (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    internal_code   VARCHAR(50),
    doc_type        VARCHAR(30) NOT NULL CHECK (
        doc_type IN ('manual', 'datasheet', 'certification', 'other')
    ),
    title           VARCHAR(300) NOT NULL,
    file_path       TEXT,
    file_url        TEXT,
    file_hash       VARCHAR(64),
    indexed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_index_code
    ON document_index (internal_code);

CREATE INDEX IF NOT EXISTS idx_document_index_type
    ON document_index (doc_type);

CREATE TABLE IF NOT EXISTS whatsapp_drafts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID REFERENCES user_sessions(id) ON DELETE SET NULL,
    easyone_user_id     VARCHAR(100) NOT NULL,
    customer_phone      VARCHAR(30),
    customer_code       VARCHAR(50),
    inbound_message     TEXT NOT NULL,
    draft_reply         TEXT NOT NULL,
    suggested_products  JSONB NOT NULL DEFAULT '[]',
    status              VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_drafts_user
    ON whatsapp_drafts (easyone_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app_releases (
    version         VARCHAR(20) PRIMARY KEY,
    download_url    TEXT NOT NULL,
    release_notes   TEXT,
    mandatory       BOOLEAN NOT NULL DEFAULT FALSE,
    published_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO app_releases (version, download_url, release_notes, mandatory)
VALUES (
    '1.0.0',
    'https://updates.macsystem.local/mac-ai-assistant/MAC_AI_Assistant_Setup_1.0.0.exe',
    'Release MVP iniziale MAC AI Assistant',
    FALSE
)
ON CONFLICT (version) DO NOTHING;

-- Seed clienti demo
INSERT INTO customer_cache (customer_code, company_name, vat_number, phone, email, city, sales_agent)
VALUES
    ('CLI001', 'Tech Solutions Srl', 'IT12345678901', '+393331112233', 'acquisti@techsolutions.it', 'Milano', 'Marco Rossi'),
    ('CLI002', 'Informatica Nord SpA', 'IT98765432109', '+393334445566', 'ordini@infnord.it', 'Torino', 'Laura Bianchi'),
    ('CLI003', 'Digital Works Snc', 'IT11223344556', '+393337778899', 'info@digitalworks.it', 'Bologna', 'Marco Rossi')
ON CONFLICT (customer_code) DO NOTHING;
